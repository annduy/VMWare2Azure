import subprocess
import os
import time
import threading
import sys
import queue


# Replace with your values###########
powershell = "C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe"
qemu_img = 'D:\\qemu-img\\qemu-img.exe'
#=== VMWare VM info
vmdk_path ='G:\\VMWare-VMs\\UbuntuServer20046'
vmdk_hdds = ['UbuntuServer20046.vmdk', 'UbuntuServer20046-0.vmdk'] # the bootable disk must be at 1st in the list!!!!

#=== Hyper-V VM info
vhd_path= "G:\\HyperV-VMs\\UbuntuServer20046"
vhd_hdds = []
#==== AZ info
az_vm_name = ''
az_hdds =[]
az_bootable_disk = ''
############################################

def obtain_vm_name(vmdk_path):
    tokens = vmdk_path.split('\\')
    vm_name = tokens[-1]
    return vm_name

def genarate_az_bootable_disk_name(bootable_vmdk_hdd):
   az_bootable_disk = bootable_vmdk_hdd.replace('.vmdk','-dsk')
   return az_bootable_disk 

def generate_vhd_hdds_and_az_hdds(vmdk_hdds):
    for vmdk_hdd in vmdk_hdds:
        vhd_hdd = vmdk_hdd.replace('.vmdk','.vhd')
        vhd_hdds.append(vhd_hdd)
        az_hdd = vmdk_hdd.replace('.vmdk','-dsk')
        az_hdds.append(az_hdd)
    return vhd_hdds, az_hdds
 

def powershell_in_subprocess(command, queue):
    result = subprocess.run([powershell,'-command',command],stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
    queue.put(result)

def run_ps_command_in_thread(command):
    global result_queue
    task = threading.Thread(target = lambda: powershell_in_subprocess(command,result_queue))
    task.start()
    task_progress(task)
    result = result_queue.get()
    if result.stdout != '':
        print("Result out from thread:", result.stdout)
    if result.stderr != '':
        print("Result error from thread:", result.stderr)  

def task_progress(task):
    while task.is_alive():
        sys.stdout.write(".")
        sys.stdout.flush()
        time.sleep(0.5)
    # Print a final newline character to ensure the last line is wrapped
    print()    


def convert_vmdks_2_vhds(vmdk_path,vmdk_hdds,vhd_path):
    try:
        if not os.path.exists(vhd_path):
            os.makedirs(vhd_path)
        for vmdk_hdd in vmdk_hdds:
            vhd_hdd = vmdk_hdd.replace('vmdk','vhd')
            convert_command = f'{qemu_img} convert -f vmdk -O vpc -o subformat=fixed {vmdk_path}\{vmdk_hdd} {vhd_path}\{vhd_hdd}'
            print(f"converting file: {vmdk_path}\{vmdk_hdd}"  )
            run_ps_command_in_thread(convert_command)
            hdd_len_in_bytes = os.path.getsize(f'{vhd_path}\{vhd_hdd}')
            if (hdd_len_in_bytes % (1024*1024)) != 0: 
                hdd_len_in_meg = ((hdd_len_in_bytes // (1024*1024)) + 1)
                resize_command = f"Resize-VHD {vhd_path}\{vhd_hdd} -SizeBytes {hdd_len_in_meg}MB"
                print(f"Resizing file: {vhd_path}\{vhd_hdd}"  )
                run_ps_command_in_thread(resize_command)
    except:
        print("Encountered an error during convert VMDKs to VHDs.")
        exit()    

def upload_vhds_2_az_storage(vhd_path,vhd_hdds):
    global az_storage,az_key, az_container, result_queue
    try:
        for vhd in vhd_hdds:
            upload_command = f"az storage blob upload --account-name {az_storage} --account-key {az_key} --container-name {az_container}  --name {vhd} --file {vhd_path}\{vhd} --overwrite true"
            print(f"Uploading file {vhd_path}\{vhd} to Azure Storage")
            run_ps_command_in_thread(upload_command)
    except:
        print("Encountered an error during uploading VHDs to Azure storage.")
        exit(0)

def create_az_disk_from_uploaded_vhd(vhd,os_type='Linux',sku='Standard_LRS'):
    global az_resourcegroup, az_storage,az_container
    az_disk = vhd.strip('.vhd') + '-dsk'
    create_az_disk_cmd = f"az disk create -g {az_resourcegroup} -n {az_disk} --os-type {os_type} --sku {sku} --source https://{az_storage}.blob.core.windows.net/{az_container}/{vhd}"
    print(f"Creating AZDisk from {vhd}")
    run_ps_command_in_thread(create_az_disk_cmd)

def create_az_disks_from_all_uploaded_vhds(vhd_hdds):
    for vhd_hdd in vhd_hdds:
        create_az_disk_from_uploaded_vhd(vhd_hdd)


def create_az_vm_from_bootable_az_disk(vm_name,az_disk, os_type='Linux', size='Standard_B1ls'):
    global az_resourcegroup
    creat_az_vm_cmd = f"az vm create -g {az_resourcegroup} -n {vm_name} --attach-os-disk {az_disk} --os-type {os_type} --size {size}"
    print(f"Creating AZ VM from {az_disk}")
    run_ps_command_in_thread(creat_az_vm_cmd)

def attach_non_bootable_disk_to_az_vm(vm_name, az_disk, sku='Standard_LRS'):
    global az_resourcegroup
    attach_disk_cmd = f"az vm disk attach --resource-group {az_resourcegroup} --vm-name {vm_name} --name {az_disk} --sku {sku}"
    print(f"Attaching {az_disk} to {vm_name}")
    run_ps_command_in_thread(attach_disk_cmd)


def delete_uploaded_vhds():
    global az_container, az_storage, az_key
    az_delete_vhds_command = f'az storage blob delete-batch --account-key {az_key} -s {az_container} --account-name {az_storage} --pattern *.vhd'
    print("Delelting all uploaded VHD(s).")
    run_ps_command_in_thread(az_delete_vhds_command)

def delete_local_vhds(vhd_path):
    delete_local_vhds_command = f'Remove-Item –path {vhd_path} –recurse'
    print("Deleting all generated VHD(s).")
    run_ps_command_in_thread(delete_local_vhds_command)


def housekeeping():
    global vhd_path
    delete_uploaded_vhds()
    delete_local_vhds(vhd_path)



az_resourcegroup = os.environ['az-resourcegroup'].strip()
az_storage = os.environ['az-storage'].strip()
az_container = os.environ["az-container"].strip()
az_key = os.environ["az-key"].strip()
result_queue = queue.Queue()
vhd_hdds, az_hdds = generate_vhd_hdds_and_az_hdds(vmdk_hdds)
az_vm_name = obtain_vm_name(vmdk_path)
az_bootable_disk = genarate_az_bootable_disk_name(vmdk_hdds[0])

#convert_vmdks_2_vhds(vmdk_path,vmdk_hdds,vhd_path)

upload_vhds_2_az_storage(vhd_path,vhd_hdds)

create_az_disks_from_all_uploaded_vhds(vhd_hdds)

create_az_vm_from_bootable_az_disk(az_vm_name,az_bootable_disk)
if len(az_hdds) > 1 : #original VM has more than 1 disk: all disk from the 2nd one are data disks
    for az_hdd in az_hdds[1::]: 
        attach_non_bootable_disk_to_az_vm(az_vm_name,az_hdd)
        
housekeeping()

print("Your have finished migrating a VMWare from your computer to Azure. Enjoy with Azure cloud, :)")
