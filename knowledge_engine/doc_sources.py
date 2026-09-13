"""
Documentation Sources Registry for AI Cortex Knowledge Engine.
Defines authoritative seeds and topics across:
1. Microsoft (learn.microsoft.com)
2. Red Hat (docs.redhat.com)
3. Linux (kernel.org, wiki.archlinux.org, tldp.org)
4. Amazon Web Services (docs.aws.amazon.com)
5. GitHub (docs.github.com, cli.github.com)
6. VMware (docs.vmware.com, developer.broadcom.com)
7. Ubuntu (ubuntu.com/server/docs)
"""

DOCUMENTATION_TARGETS = {
    "microsoft": {
        "domain": "learn.microsoft.com",
        "search_queries": [
            "site:learn.microsoft.com windows server active directory administration guide",
            "site:learn.microsoft.com powershell core cmdlets automation reference",
            "site:learn.microsoft.com azure cli az command reference virtual machines",
            "site:learn.microsoft.com windows server hyper-v switch configuration",
            "site:learn.microsoft.com dynamics 365 business central developer admin itpro",
            "site:learn.microsoft.com windows server dns dhcp failover setup",
            "site:learn.microsoft.com iis administration powershell web administration",
            "site:learn.microsoft.com remote desktop services connection broker rdp gateway"
        ],
        "seed_urls": [
            "https://learn.microsoft.com/en-us/windows-server/identity/ad-ds/get-started/virtual-dc/active-directory-domain-services-overview",
            "https://learn.microsoft.com/en-us/powershell/scripting/overview",
            "https://learn.microsoft.com/en-us/windows-server/virtualization/hyper-v/hyper-v-technology-overview",
            "https://learn.microsoft.com/en-us/windows-server/networking/technologies/netsh/netsh-contexts",
            "https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/windows-commands",
            "https://learn.microsoft.com/en-us/troubleshoot/windows-server/performance/troubleshoot-high-cpu-usage-guidance"
        ]
    },
    "redhat": {
        "domain": "docs.redhat.com",
        "search_queries": [
            "site:docs.redhat.com red hat enterprise linux 9 system administration guide",
            "site:docs.redhat.com rhel 9 systemd service unit configuration",
            "site:docs.redhat.com rhel 9 selinux managing booleans policies context",
            "site:docs.redhat.com rhel 9 podman rootless containers systemd",
            "site:docs.redhat.com rhel 9 dnf package management repositories",
            "site:docs.redhat.com rhel 9 cockpit web console install configure",
            "site:docs.redhat.com rhel 9 high availability cluster pacemaker corosync",
            "site:docs.redhat.com rhel 9 networkmanager nmcli connection configuration"
        ],
        "seed_urls": [
            "https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/configuring_basic_system_settings/managing-system-services-with-systemctl_configuring-basic-system-settings",
            "https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/using_selinux/getting-started-with-selinux_using-selinux",
            "https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/managing_software_with_the_dnf_tool/index",
            "https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/configuring_and_managing_networking/getting-started-with-nmcli_configuring-and-managing-networking",
            "https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/building_running_and_managing_containers/index"
        ]
    },
    "linux": {
        "domain": "kernel.org / archlinux.org / tldp.org",
        "search_queries": [
            "site:docs.kernel.org admin-guide sysctl networking tunables",
            "site:wiki.archlinux.org systemd journalctl troubleshooting service unit",
            "site:wiki.archlinux.org iproute2 network configuration routing vlan",
            "site:wiki.archlinux.org nftables firewall rules configuration guide",
            "site:wiki.archlinux.org lvm logical volume manager creation expansion",
            "site:docs.kernel.org admin-guide blockdev lvm md raid",
            "site:man7.org linux man pages proc sysctl fs ext4"
        ],
        "seed_urls": [
            "https://docs.kernel.org/admin-guide/sysctl/net.html",
            "https://docs.kernel.org/admin-guide/perf/index.html",
            "https://wiki.archlinux.org/title/Systemd",
            "https://wiki.archlinux.org/title/Network_configuration",
            "https://wiki.archlinux.org/title/Nftables",
            "https://wiki.archlinux.org/title/LVM"
        ]
    },
    "aws": {
        "domain": "docs.aws.amazon.com",
        "search_queries": [
            "site:docs.aws.amazon.com aws cli command reference ec2 s3 iam vpc",
            "site:docs.aws.amazon.com amazon ec2 user guide linux instances security groups",
            "site:docs.aws.amazon.com amazon s3 user guide bucket policies replication",
            "site:docs.aws.amazon.com iam user guide policy evaluation json examples",
            "site:docs.aws.amazon.com amazon vpc route tables subnets internet gateway",
            "site:docs.aws.amazon.com systems manager ssm session manager linux",
            "site:docs.aws.amazon.com cloudwatch agent metrics logs configuration"
        ],
        "seed_urls": [
            "https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-welcome.html",
            "https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/concepts.html",
            "https://docs.aws.amazon.com/AmazonS3/latest/userguide/Welcome.html",
            "https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html",
            "https://docs.aws.amazon.com/vpc/latest/userguide/what-is-amazon-vpc.html",
            "https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/WhatIsCloudWatch.html"
        ]
    },
    "github": {
        "domain": "docs.github.com",
        "search_queries": [
            "site:docs.github.com github actions workflow syntax jobs steps matrix",
            "site:cli.github.com gh command line manual reference repo pr issue",
            "site:docs.github.com connecting to github with ssh key passphrase agent",
            "site:docs.github.com git branching rebasing resolving merge conflicts",
            "site:docs.github.com github actions runner self-hosted installation",
            "site:docs.github.com github webhooks security secret validation",
            "site:docs.github.com github rest api authentication rate limits curl"
        ],
        "seed_urls": [
            "https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions",
            "https://cli.github.com/manual/",
            "https://docs.github.com/en/actions/hosting-your-own-runners/managing-self-hosted-runners/about-self-hosted-runners",
            "https://docs.github.com/en/rest/quickstart",
            "https://docs.github.com/en/authentication/connecting-to-github-with-ssh/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent"
        ]
    },
    "vmware": {
        "domain": "docs.vmware.com / broadcom.com",
        "search_queries": [
            "site:docs.vmware.com vsphere esxi 8.0 host administration configuration",
            "site:docs.vmware.com vcenter server 8.0 cluster ha drs management",
            "site:docs.vmware.com vsphere networking vswitch distributed switch port groups",
            "site:docs.vmware.com esxi storage vmfs datastore expand iscsi nfs",
            "site:developer.broadcom.com powercli cmdlets connect-viserver get-vm start-vm",
            "site:kb.vmware.com esxi promiscuous mode forged transmits mac changes vlan 4095",
            "site:docs.vmware.com esxcli network ip interface command reference"
        ],
        "seed_urls": [
            "https://docs.vmware.com/en/VMware-vSphere/8.0/vsphere-esxi-installation-setup/GUID-B0EB0112-92AE-4395-927A-93E582EBE039.html",
            "https://docs.vmware.com/en/VMware-vSphere/8.0/vsphere-vcenter-installation/GUID-F5268803-9E0C-413E-A022-9164276A5271.html",
            "https://docs.vmware.com/en/VMware-vSphere/8.0/vsphere-networking/GUID-350344DE-483A-42ED-B0E2-C81111E0E162.html",
            "https://docs.vmware.com/en/VMware-vSphere/8.0/vsphere-storage/GUID-8CC0AE39-9599-4A00-84E3-72C00E19B214.html",
            "https://kb.vmware.com/s/article/1004099"
        ]
    },
    "ubuntu": {
        "domain": "ubuntu.com/server/docs",
        "search_queries": [
            "site:ubuntu.com/server/docs netplan network configuration bridge bonding static ip",
            "site:ubuntu.com/server/docs ufw firewall rules ports rate limit allow",
            "site:ubuntu.com/server/docs package management apt dpkg sources list",
            "site:ubuntu.com/server/docs security automatic unattended-upgrades",
            "site:ubuntu.com/server/docs service management systemd systemctl journalctl",
            "site:ubuntu.com/server/docs storage lvm raid zfs btrfs configuration",
            "site:ubuntu.com/server/docs openssh server sshd_config hardening"
        ],
        "seed_urls": [
            "https://ubuntu.com/server/docs",
            "https://ubuntu.com/server/docs/configuring-networks",
            "https://ubuntu.com/server/docs/security-firewall",
            "https://ubuntu.com/server/docs/package-management",
            "https://ubuntu.com/server/docs/service-management",
            "https://ubuntu.com/server/docs/security-automatic-updates"
        ]
    }
}
