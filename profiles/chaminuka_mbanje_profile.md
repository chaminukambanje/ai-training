# Chaminuka Mbanje - Professional Biography, Roles, and Expertise

## 1. Identity & Overview
* **Full Name:** Chaminuka Munashe Mbanje (commonly known as Chaminuka Mbanje or Chami; username `mbanjec`).
* **Location:** Oxfordshire, United Kingdom.
* **Email:** mbanjec@gmail.com
* **Phone:** +44 7565 297807
* **LinkedIn:** https://www.linkedin.com/in/chaminukambanje/
* **GitHub:** https://github.com/chaminukambanje
* **Personal Portal & Learning Hub:** https://chaminuka.npcsolutions.co.uk (hosted on local homelab `192.168.0.218:8089`)

## 2. Current Primary Role & Institutional Affiliation
* **Role:** Storage Operations and User Support Specialist at **JASMIN**.
* **Institutions & Organisations:**
  * **CEDA:** Centre for Environmental Data Analysis
  * **NCAS:** National Centre for Atmospheric Science (UKRI / NERC)
  * **STFC:** Science and Technology Facilities Council (part of UK Research and Innovation - UKRI)
  * **Facility Location:** Rutherford Appleton Laboratory (RAL), Harwell Campus, Didcot, Oxfordshire, UK.
* **JASMIN Supercomputing & Data Analysis Responsibilities:**
  * Administering and optimizing **Group Workspaces (GWS)** with multi-petabyte storage allocations and strict access control for climate, atmospheric, and earth observation science teams across the UK and worldwide.
  * Operational support across high-performance parallel file systems and storage tiers: **Panasas**, **Ceph** object storage, **Quobyte**, and archival tape tiers.
  * Supporting scientific users with high-throughput computational workflows: **SLURM** batch cluster job submission, MPI parallel jobs, and **Globus** / **Dufs** secure data exchange.

## 3. Microsoft Certifications & Elite Instructor Standing
Chaminuka Mbanje is a **Microsoft Certified Trainer (MCT)** with a comprehensive suite of expert and associate certifications:
* **MCT:** Microsoft Certified Trainer (Elite Instructor in Azure, Dynamics 365, and Power Platform)
* **DevOps Engineer Expert:** AZ-400 (CI/CD, Azure Pipelines, Git, infrastructure as code)
* **Dynamics 365 Business Central:** MB-800 Functional Consultant Associate (Finance, Operations, Supply Chain, AL language development)
* **Azure Data Engineer Associate:** DP-203 (Azure Synapse Analytics, Databricks, Data Factory, ADLS Gen2)
* **Azure Data Scientist Associate:** DP-100 (Azure Machine Learning, model training, ML pipelines)
* **Azure Security Engineer Associate:** AZ-500 (Cloud security posture, IAM, network security, Key Vault)
* **Azure Administrator Associate:** AZ-104 (Identities, governance, compute, storage, virtual networks)
* **Azure Developer Associate:** AZ-204 (Cloud solutions development, SDKs, event-driven architectures)
* **Power Platform Developer Associate:** PL-400 (Power Apps, PCF controls, plugins, custom connectors)
* **Power Platform Functional Consultant:** PL-200 (Model-driven apps, Canvas apps, Power Automate, Dataverse)
* **Database Development:** MCSA: SQL 2016 Database Development (T-SQL, query tuning, relational modeling)
* **Dynamics 365 + Power Platform Solution Architect:** Expert enterprise architecture & integrations
* **Official Microsoft Transcript Verification:** Transcript ID: `1237645` | Access Code: `Munashe1234` (validated at `https://mcp.microsoft.com/Anonymous//Transcript/Validate`)

## 4. Professional Career Journey (25+ Years Experience)
* **July 2023 – Present:** Storage Operations and User Support Specialist (JASMIN), Centre for Environmental Data Analysis (CEDA) / UKRI-STFC / NCAS, Oxfordshire, UK.
* **2019 – Present:** Director of Infrastructure & Development, NPC Cloud Solutions Services Ltd (Cloud migrations, hybrid network configurations, enterprise Active Directory, Microsoft 365).
* **2020 – Present:** Senior Technical Facilitator & Microsoft Certified Trainer (MCT), Mercer Inter Ed (Delivering official Azure, Data Engineering, and Power Platform curricula).
* **2019 – 2020:** Head of Program: IT Cloud Solution Administration & Cloud Engineering, CTU Training Solutions, Pretoria, South Africa (Supervised engineering staff across 14 nationwide campuses; taught MCSE and Cloud Engineering).
* **2016 – 2018:** Lecturer in Information Technology, Damelin Menlyn Campus, Pretoria (Taught undergraduate BCom Information Management and Diploma in IT).
* **2015 – 2016:** Campus Manager & Technical Facilitator, Richfield Graduate Institute of Technology (RGI / PC Training).
* **2010 – 2015:** Software Engineer & Systems Administrator, National University of Science and Technology (NUST), Bulawayo (Managed enterprise IT for 10,000+ students and 1,500 staff; implemented Microsoft Dynamics NAV 2009 ERP on MS SQL; architected VMware vSphere environment with 12 physical hosts and 55+ VMs).
* **2009 – 2010:** ICT Manager, Bindura University of Science and Education (BUSE) (Led university IT department, campus wireless, and VSAT telecommunications).
* **1996 – 2006:** Mathematics & Computer Studies Teacher, Luveve / Pumula / Sontala High Schools (GCSE-O & A Level education; established deep pedagogical foundations).

## 5. Academic Degrees & Education
* **Master of Science Studies (Computer Science):** UNICAF University (Specialization in Distributed Systems, Advanced Database Systems, and Machine Learning).
* **B.Sc. (Honours) in Computer Science:** National University of Science and Technology (NUST), Bulawayo, Zimbabwe.
* **Diploma in Information Processing:** City & Guilds of London Institute (1997–1999).
* **Diploma in Education (Mathematics):** Gweru Teacher's College (1994–1995).
* **Professional Board Accreditation:** MIITPSA (Member of the Institute of Information Technology Professionals South Africa, Member #M051264, Critical Skills Assessment CSA1926).
* **Languages:** English (Fluent), Shona, Ndebele, Chewa, Zulu, Bemba, and SiSwati (7 languages).

## 6. Private Homelab Infrastructure Architecture
Chaminuka Mbanje designed, built, and maintains an enterprise-tier homelab across subnet `192.168.0.0/24`:
1. **Network Gateway:** Sky Broadband Hub (`192.168.0.1`).
2. **Primary Hypervisor:** `esxi-01.npcsolutions.co.za` (`192.168.0.200`), Dell PowerEdge R620 with dual Intel Xeon E5-2660 v2 CPUs (40 logical cores), 240 GB physical RAM, VMware ESXi 8.0.3, hosting 15 virtual machines.
3. **Enterprise Storage & Packet Monitoring:** `truenas.local` (`192.168.0.47`), TrueNAS SCALE, ZFS pool1, exporting `/mnt/scratch` NFS share to the Slurm cluster, and passively capturing network traffic via unnumbered interface `ens224`.
4. **Application & Monitoring Server:** `docker.npcsolutions.co.uk` (`192.168.0.218`), 60 GB RAM, running Wazuh SIEM, Prometheus (9090), Grafana (3002), WireGuard VPN (51820), Booklore library (6060), and personal learning hub.
5. **Private AI Server:** `ai-cortex-01` (`192.168.0.235`), 16 vCPUs, 43 GB RAM, hosting Ollama (11434), FastAPI grounded server (8000), continuous documentation learning daemon (`ai-docs-trainer`), and SQLite FTS5 knowledge base.
6. **Slurm HPC Cluster:** Head nodes `login-01` (`192.168.0.131`) and `login-02` (`192.168.0.133`), and compute worker nodes `node-01` through `node-06` (`192.168.0.170`, `192.168.0.53`, `192.168.0.124`, `192.168.0.227`, `192.168.0.125`, `192.168.0.146`).
7. **Databases & Business Systems:** Microsoft SQL Server 2022 (`192.168.0.237`), Microsoft Dynamics 365 Business Central ERP (`192.168.0.39`), and UNICAF academic VM (`192.168.0.213`).
