#!/usr/bin/env python3
"""Seed the resume text into the profile."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from database import SessionLocal
from models import Profile

RESUME = """QUALIFICATIONS
IT professional with 5+ years of enterprise-level experience managing 750+ endpoints, 8 print servers, and 250 printers. Advanced expertise in Microsoft Endpoint Configuration Manager (MECM), PowerShell scripting, and Citrix environment management. Proven track record in implementing and maintaining mobile device management solutions for 150+ Zebra handheld scanners. Skilled in leveraging AI tools to automate and optimize IT processes.

SKILLS
Scripting & Automation: PowerShell (Advanced Functions, Object Creation), PSAppDeployToolkit, Python (OpenAI API Integration), Batch Scripting
Operating Systems: Windows Server, Windows Desktop (All recent versions)
Virtualization: VMware vSphere, Hyper-V
Networking: TCP/IP, DNS, DHCP Configuration, Cisco Device Experience, Enterprise Print Infrastructure Management
Hardware & Troubleshooting: Workstation Deployment, Hardware Repair, Malware Remediation, System Building
Soft Skills: Problem-Solving, Technical Training & Mentoring, Cross-functional Communication, Team Collaboration

PROFESSIONAL EXPERIENCE
IT Systems Administrator | WSI, Appleton, WI | 2019 - December 2024
- Managed comprehensive endpoint environment of 750+ devices using MECM
- Administered enterprise print infrastructure spanning 8 print servers and 250 printers
- Developed PowerShell scripts utilizing PSAppDeployToolkit for automated deployment
- Maintained and optimized Citrix environment
- Implemented mobile device deployment for 150+ Zebra handheld scanners using Mobi MDM
- Leveraged AI tools (ChatGPT, GitHub Copilot, Claude) for automation
- Configured and maintained VMware vSphere and Hyper-V environments
- Provided technical training and mentorship

Remote IT Administrator | Show Secretary Services, Eau Claire, WI | 2007 - 2019
- Remote technical support and systems administration
- Hardware upgrades including SSD deployments
- Network configuration and maintenance
- Technology acquisitions consulting

Warehouse Systems Specialist | Back in Black, Neenah, WI | 2012 - 2019
- Inventory databases using OpenOffice Base
- Barcode scanning systems configuration
- Warehouse management system implementation

EDUCATION
BFA Media Arts and Animation - Illinois Institute of Art-Schaumburg (GPA: 3.6)
AAS Graphic Design - American Academy of Art, Chicago"""

db = SessionLocal()
try:
    profile = db.query(Profile).first()
    if not profile:
        profile = Profile()
        db.add(profile)
    profile.resume_text = RESUME
    db.commit()
    print(f"Resume seeded ({len(RESUME)} chars)")
finally:
    db.close()
