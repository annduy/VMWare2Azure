import subprocess

cmd = 'az vm create -g SDWan -n UbuntuServer20046-vm --attach-os-disk UbuntuServer20046-dsk --size Standard_B1ls --os-type Linux --public-ip-sku Standard'

result = subprocess.run(['powershell', '-command', cmd], stderr=subprocess.PIPE, text=True)

# Print the error output
print(result.stderr)

