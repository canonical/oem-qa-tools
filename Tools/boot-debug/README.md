# **Automated System Management Script**

<!-- markdownlint-disable MD013 -->
This Python script, boot\_debug.py, creates and manages a systemd service for automated, cyclical system reboots or wake-up cycles. It's designed to be a robust debugging tool for scenarios where a system needs to perform a specific action (like a reboot cycle) a set number of times.  
The service is configured to execute a main command after a specified delay and can be set to run an optional pre-execution script.

## **Features**

* **Reboot or Wake-up Cycle:** Choose between systemctl reboot (wb) or rtcwake \-m off \-s 120 (cb).  
* **Configurable Delay:** Set a delay in seconds before the main wb/cb command is executed.  
* **Max Cycle Limit:** Define the maximum number of times the service will run. The service will automatically stop and disable itself once this limit is reached.  
* **Optional Pre-execution Script:** Provide an absolute path to a shell script to run before the main command. If this script returns a non-zero exit code, the service will stop and disable itself immediately.

## **Usage**

This script must be run with sudo as it manages systemd services.

### **Create the Service**

To create the service, use the create action. You must specify the main command with the \--command flag.  
Basic Example:  
Create a service that reboots the system (wb) after a 60-second delay. The service will run a maximum of 5 times.  
sudo python3 boot\_debug.py create \--command wb

Advanced Example:  
Create a service that suspends and wakes the system after a 120-second delay (cb), with a maximum of 3 cycles. It will also run a pre-execution script located at /home/user/my\_check\_script.sh.  
sudo python3 boot\_debug.py create \--command cb \--delay 120 \--max-cycles 3 \--extra-script /home/user/my\_check\_script.sh

### **Remove the Service**

To remove the service and its associated files, use the remove action.  
sudo python3 boot\_debug.py remove

## **Command-Line Arguments**

| Argument | Description | Required for create | Default Value |
| :---- | :---- | :---- | :---- |
| action | create or remove | Yes | N/A |
| \--command | The main command to execute. Valid options are wb (reboot) or cb (suspend/wake). | Yes | wb |
| \--delay | Delay in seconds before execution of the main command. | No | 60 |
| \--max-cycles | Maximum number of cycles for the service. | No | 5 |
| \--extra-script | Absolute path to an optional script to run before the main command. | No | N/A |

## **Service Information**

* **Service File Path:** /etc/systemd/system/reboot-manager.service  
* **Helper Script Path:** /usr/local/bin/reboot\_manager.sh  
* **Cycle Counter Path:** /var/lib/reboot\_manager/cycle\_count

## **Logging and Status**

You can monitor the service's status and logs with the following commands:

* **Check status:** systemctl status reboot-manager.service  
* **View logs:** journalctl \-u reboot-manager.service

## **Re-executing this script**

You have to execute `Remove the Service` to clean up the environment first.
