import subprocess

cmd = 'az storage blob upload --account-name annduystorage --account-key G3Jc6uGXicw7QMZDIJYDZC/aeNFUzzpznVsNaFUd9wBdrjDCA2flwzCAXsP/CRYrPX63R6bguoZJ+AStqd/Fgw== --container-name uploadstorage  --name UbuntuServer20046.hdd --file G:\\HyperV-VMs\\UbuntuServer20046\\UbuntuServer20046.hdd'

result = subprocess.run(['powershell', '-command', cmd], stderr=subprocess.PIPE, text=True)

# Print the error output
print(result.stderr)

# def obtain_vm_name(vmdk_path):
#     tokens = vmdk_path.split('\\')
#     vm_name = tokens[-1]
#     print(vm_name)
#     return vm_name



# az_vm_name = obtain_vm_name('G:\\VMWare-VMs\\UbuntuServer20046')
# print(az_vm_name)