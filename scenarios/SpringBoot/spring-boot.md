# SpringBootDemo

Spring Boot application that we will deploy to Kubernetes clusters in Azure.

## Deploying to VM

### Create and connect to the VM 

Log in and create VM: 

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export RESOURCE_GROUP="SpringBoot$RANDOM_ID"
export REGION="westus2"

az group create --name ${RESOURCE_GROUP} --location ${REGION}
```

```bash
export VM_NAME="springboot-vm$RANDOM_ID"
export ADMIN_USERNAME="vm-admin-name$RANDOM_ID"
export VM_IMAGE="Ubuntu2204"

az vm create \
  --resource-group ${RESOURCE_GROUP} \
  --name ${VM_NAME} \
  --image ${VM_IMAGE} \
  --admin-username ${ADMIN_USERNAME} \
  --generate-ssh-keys \
  --public-ip-sku Standard --size standard_d4s_v3
```

Store the VM IP address for later: 

```bash
export VM_IP_ADDRESS=`az vm show -d -g ${RESOURCE_GROUP} -n ${VM_NAME} --query publicIps -o tsv` 
```

Run the following to open port 8080 on the vm since SpringBoot uses it

```bash
az vm open-port --port 8080 --resource-group ${RESOURCE_GROUP} --name ${VM_NAME} --priority 1100
```

Connect to the VM: 

```bash
ssh -o StrictHostKeyChecking=no -t ${ADMIN_USERNAME}@${VM_IP_ADDRESS}
```

### Deploy the application

Install Java and maven needed for application

```bash
sudo apt-get update
sudo apt-get install default-jdk
sudo apt-get install maven
```

Now it's time to clone the project into the vm and give it proper permissions: 

```bash
cd /opt
sudo git clone https://github.com/dasha91/SpringBootDemo
cd SpringBootDemo
sudo chmod -R 777 /opt/SpringBootDemo/
```

Run and deploy the app

```bash
mvn clean install
mvn spring-boot:run  
```

### Verify the application

Finally, go to http://[$VM_IP_ADDRESS]:8080 to confirm that it's working :D :D :D

To verify if the application is running, you can use the `curl` command:

```bash
curl http://[$VM_IP_ADDRESS]:8080
```

If the application is running, you should see the HTML content of the Spring Boot application's home page.