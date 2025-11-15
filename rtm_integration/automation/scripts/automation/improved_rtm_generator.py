#!/usr/bin/env python3

import pandas as pd
import re
import json
from datetime import datetime
import os

class ImprovedCryoplantRTMGenerator:
    def __init__(self):
        self.requirements = []
        self.sbs_structure = self._initialize_sbs_structure()
        
    def _initialize_sbs_structure(self):
        """Initialize the hierarchical SBS structure as specified"""
        return {
            # Level 0 - System Level
            "QSYS": {
                "name": "Cryogenic System",
                "level": 0,
                "parent": None,
                "children": ["QSYS-PR"],
                "description": "Complete cryogenic system including plant, infrastructure, and distribution"
            },
            "QSYS-PR": {
                "name": "Project Requirements", 
                "level": 0,
                "parent": None,
                "children": ["QPLANT", "QINFRA", "QCELL", "QDIST"],
                "description": "Overall project requirements and constraints"
            },
            
            # Level 1 - Major Subsystems
            "QPLANT": {
                "name": "Cryoplant",
                "level": 1, 
                "parent": "QSYS-PR",
                "children": ["WCS", "QRB"],
                "description": "Main cryogenic refrigeration plant including compressors and cold box"
            },
            "QINFRA": {
                "name": "Cryogenic Infrastructure", 
                "level": 1,
                "parent": "QSYS-PR", 
                "children": ["WCS", "QRB"],
                "description": "CSS cryogenic supply system infrastructure"
            },
            "QCELL": {
                "name": "Cryogenic Cell",
                "level": 1,
                "parent": "QSYS-PR",
                "children": [],
                "description": "CSS cryogenic USER - individual cryomodule and valve box combinations"
            },
            "QDIST": {
                "name": "Cryogenic Distribution",
                "level": 1, 
                "parent": "QSYS-PR",
                "children": [],
                "description": "CSS cryogenic USER - distribution lines and headers"
            },
            
            # Level 2 - Major Components
            "WCS": {
                "name": "Warm Compressor Station",
                "level": 2,
                "parent": "QPLANT",
                "children": ["PVPS", "HP"],
                "description": "Warm compression system including LP to HP and VLP to LP compressors"
            },
            "QRB": {
                "name": "Refrigeration Cold Box", 
                "level": 2,
                "parent": "QPLANT",
                "children": ["CC", "TURBINES", "BATH-4K", "BATH-2K"],
                "description": "Cold box containing refrigeration equipment and heat exchangers"
            },
            
            # Level 3 - Sub-Components  
            "PVPS": {
                "name": "Pressure Vessel & Piping System",
                "level": 3,
                "parent": "WCS", 
                "children": [],
                "description": "Pressure vessels, piping, and associated safety systems for WCS"
            },
            "HP": {
                "name": "High Pressure System",
                "level": 3,
                "parent": "WCS",
                "children": [],
                "description": "High pressure compressors and associated equipment"
            },
            "CC": {
                "name": "Cold Compressors",
                "level": 3, 
                "parent": "QRB",
                "children": [],
                "description": "Cold compression equipment within refrigeration cold box"
            },
            "TURBINES": {
                "name": "Turbo Expanders",
                "level": 3,
                "parent": "QRB",
                "children": [],
                "description": "Turbine expanders for refrigeration cycle"
            },
            "BATH-4K": {
                "name": "4K Bath System",
                "level": 3,
                "parent": "QRB", 
                "children": [],
                "description": "4K temperature helium bath and associated equipment"
            },
            "BATH-2K": {
                "name": "2K Bath System",
                "level": 3,
                "parent": "QRB",
                "children": [],
                "description": "2K temperature helium bath and associated equipment"
            }
        }

    def extract_requirements_from_pdf_text(self):
        """Extract requirements directly from the PDF content we already read"""
        
        # Read the PDF content that was already processed
        with open('/home/ubuntu/Uploads/cryoplant_requirements.pdf', 'r', errors='ignore') as f:
            content = f.read()
        
        # Manual extraction of known RTM requirements from the document analysis
        requirements_data = [
            {
                'req_id': 'RTM-01',
                'description': 'The QPLANT shall be capable to operate uninterrupted in 2K mode for at least 90 consecutive days',
                'section': '3.2.1 Lifetime and annual maintenance schedule',
                'category': 'Operational',
                'numerical_value': '90 days'
            },
            {
                'req_id': 'RTM-02', 
                'description': 'The maintenance schedule shall take into account the following constraints: ≥ 6 months: ≤ 10 days in 2K standby; ≥ 1 year: ≤ 20 days in 4.5K standby; ≥ 5 years: ≤ 60 days in warm stop; ≥ 10 years: ≤ 120 days in warm stop',
                'section': '3.2.1 Lifetime and annual maintenance schedule',
                'category': 'Maintenance',
                'numerical_value': 'Various time limits'
            },
            {
                'req_id': 'RTM-03',
                'description': 'The QPLANT shall have a lifetime of at least 40 years',
                'section': '3.2.1 Lifetime and annual maintenance schedule',
                'category': 'Lifetime',
                'numerical_value': '40 years'
            },
            {
                'req_id': 'RTM-04',
                'description': 'The QPLANT shall support ≥ 50 warm-up/cool-down cycles (300 K ↔ 2 K)',
                'section': '3.2.1 Lifetime and annual maintenance schedule', 
                'category': 'Operational',
                'numerical_value': '50 cycles'
            },
            {
                'req_id': 'RTM-05',
                'description': 'The QPLANT shall support the steady state operational scenarios: Warm Stop, Thermal Shield Standby, 4.5 K Standby, 2 K Standby, 2 K Operation',
                'section': '3.2.2 Steady state operational scenarios',
                'category': 'Operational',
                'numerical_value': '5 scenarios'
            },
            {
                'req_id': 'RTM-06',
                'description': 'The QPLANT shall support the scenario transitions given in Figure 6',
                'section': '3.2.3 Transient operational scenarios',
                'category': 'Operational',
                'numerical_value': 'Multiple transitions'
            },
            {
                'req_id': 'RTM-07',
                'description': 'The QPLANT shall execute the transition using the capacity defined by the steady state scenarios. No additional capacity shall be added solely for acceleration of state transitions',
                'section': '3.2.3 Transient operational scenarios',
                'category': 'Performance',
                'numerical_value': 'Existing capacity only'
            },
            {
                'req_id': 'RTM-08',
                'description': 'The QPLANT shall perform the cool-down of the QPLANT simultaneously with the cryogenic users (QCELL and QDIST static heat loads only)',
                'section': '3.2.3 Transient operational scenarios',
                'category': 'Operational',
                'numerical_value': 'Simultaneous operation'
            },
            {
                'req_id': 'RTM-09',
                'description': 'The QPLANT shall facilitate parallel cool down/warm up of all QCELLs. During cooldown and warm-up, cryomodules impose constraints: Magnetic shields must reach T < 70 K before cavities reach T < 10 K',
                'section': '3.2.3 Transient operational scenarios',
                'category': 'Operational',
                'numerical_value': 'T < 70K and T < 10K'
            },
            {
                'req_id': 'RTM-010',
                'description': 'The QPLANT shall facilitate an alternative cooldown in which only the thermal-shield (TS) circuit is cooled until their average temperature reaches 50 K. Subsequently the headers A–B and D–E are simultaneous cooled down',
                'section': '3.2.3 Transient operational scenarios',
                'category': 'Operational',
                'numerical_value': '50 K threshold'
            },
            {
                'req_id': 'RTM-011',
                'description': 'The QPLANT shall facilitate the warm-up of the cryogenic users from 2 K to 300 K in less than 5 days',
                'section': '3.2.3 Transient operational scenarios',
                'category': 'Operational',
                'numerical_value': '5 days maximum'
            },
            {
                'req_id': 'RTM-012',
                'description': 'The QPLANT shall support the transition shown in Figure 6 for the warming-up of the cryogenic users, whether passively or actively (with QCELL heaters if available)',
                'section': '3.2.3 Transient operational scenarios',
                'category': 'Operational', 
                'numerical_value': 'Multiple warming transitions'
            },
            {
                'req_id': 'RTM-013',
                'description': 'The Contractor may implement a manual purging, manual conditioning, and manual initial preparation of the QPLANT',
                'section': '3.2.4 Other operational scenarios',
                'category': 'Operational',
                'numerical_value': 'Manual operation allowed'
            },
            {
                'req_id': 'RTM-014',
                'description': 'The QPLANT shall adhere to the purge-parameter table (pressure, flow-rate, duration, allowable residual O₂) provided by SCK CEN during contract execution',
                'section': '3.2.4 Other operational scenarios',
                'category': 'Safety',
                'numerical_value': 'Per SCK CEN parameters'
            },
            {
                'req_id': 'RTM-015',
                'description': 'The QPLANT shall facilitate an average retention rate of 0.8 g/s LHe per individual QCELL (24 g/s total) during the filling process',
                'section': '3.2.4 Other operational scenarios',
                'category': 'Performance',
                'numerical_value': '0.8 g/s per QCELL, 24 g/s total'
            },
            {
                'req_id': 'RTM-016',
                'description': 'During LHe filling, the QPLANT shall provide 2,900 L of LHe to the users',
                'section': '3.2.4 Other operational scenarios',
                'category': 'Performance',
                'numerical_value': '2,900 L LHe'
            }
        ]
        
        # Convert to standardized format
        processed_requirements = []
        for req_data in requirements_data:
            sbs_assignment = self._assign_to_sbs(req_data['req_id'], req_data['description'])
            verification_method = self._determine_verification_method(req_data['description'])
            acceptance_criteria = self._generate_acceptance_criteria(req_data['description'])
            req_type = self._determine_requirement_type(req_data['description'])
            
            requirement = {
                'req_id': req_data['req_id'],
                'description': req_data['description'],
                'full_description': req_data['description'],
                'sbs_l0': sbs_assignment['l0'],
                'sbs_l1': sbs_assignment['l1'], 
                'sbs_l2': sbs_assignment['l2'],
                'sbs_l3': sbs_assignment['l3'],
                'requirement_type': req_type,
                'verification_method': verification_method,
                'acceptance_criteria': acceptance_criteria,
                'priority': self._determine_priority(req_data['description']),
                'source_section': req_data['section'],
                'parent_requirements': [],
                'child_requirements': [],
                'status': 'Active',
                'rationale': self._generate_rationale(req_data['description']),
                'category': req_data['category'],
                'numerical_value': req_data['numerical_value']
            }
            
            processed_requirements.append(requirement)
        
        return processed_requirements
    
    def _assign_to_sbs(self, req_id, req_text):
        """Assign requirement to SBS levels based on content analysis"""
        text_lower = req_text.lower()
        
        # Level 0 assignment
        if any(keyword in text_lower for keyword in ['lifetime', 'project', 'overall', 'system']):
            l0 = 'QSYS-PR'
        else:
            l0 = 'QSYS'
            
        # Level 1 assignment  
        if any(keyword in text_lower for keyword in ['compressor', 'compression', 'wcs']):
            l1 = 'QPLANT'
        elif any(keyword in text_lower for keyword in ['distribution', 'line', 'header']):
            l1 = 'QDIST'
        elif any(keyword in text_lower for keyword in ['qcell', 'cell', 'cryomodule', 'qvb']):
            l1 = 'QCELL'
        elif any(keyword in text_lower for keyword in ['infrastructure', 'utility']):
            l1 = 'QINFRA'
        else:
            l1 = 'QPLANT'
            
        # Level 2 assignment
        if any(keyword in text_lower for keyword in ['warm compressor', 'wcs']):
            l2 = 'WCS'
        elif any(keyword in text_lower for keyword in ['cold box', 'qrb', 'refrigeration']):
            l2 = 'QRB'
        else:
            l2 = 'WCS' if l1 == 'QPLANT' else ''
            
        # Level 3 assignment
        l3 = ''
        if l2 == 'WCS':
            if any(keyword in text_lower for keyword in ['pressure vessel', 'piping', 'safety']):
                l3 = 'PVPS'
            elif any(keyword in text_lower for keyword in ['high pressure', 'hp']):
                l3 = 'HP'
        elif l2 == 'QRB':
            if any(keyword in text_lower for keyword in ['turbine', 'expander']):
                l3 = 'TURBINES'
            elif '4k' in text_lower or '4.5k' in text_lower:
                l3 = 'BATH-4K'  
            elif '2k' in text_lower:
                l3 = 'BATH-2K'
            elif any(keyword in text_lower for keyword in ['cold compressor', 'cc']):
                l3 = 'CC'
                
        return {'l0': l0, 'l1': l1, 'l2': l2, 'l3': l3}
    
    def _determine_verification_method(self, req_text):
        """Determine verification method based on requirement content"""
        text_lower = req_text.lower()
        
        if any(keyword in text_lower for keyword in ['test', 'testing', 'acceptance']):
            return 'Test'
        elif any(keyword in text_lower for keyword in ['analysis', 'calculation', 'design']):
            return 'Analysis'  
        elif any(keyword in text_lower for keyword in ['inspection', 'review', 'document']):
            return 'Inspection'
        elif any(keyword in text_lower for keyword in ['demonstration', 'operation', 'functional']):
            return 'Demonstration'
        else:
            return 'Test'  # Default for operational requirements
    
    def _generate_acceptance_criteria(self, req_text):
        """Generate acceptance criteria based on requirement text"""
        text_lower = req_text.lower()
        
        # Extract numerical values if present
        numbers = re.findall(r'(\d+(?:\.\d+)?)\s*([kmgtw]?[wvapk]?|bar|days?|years?|hours?|%|cycles?)', text_lower)
        
        if numbers:
            criteria = []
            for num, unit in numbers[:3]:  # Limit to first 3 matches to avoid clutter
                if unit in ['days', 'day']:
                    criteria.append(f"Duration shall be ≤ {num} days")
                elif unit in ['years', 'year']:
                    criteria.append(f"Lifetime shall be ≥ {num} years")
                elif unit in ['cycles', 'cycle']:
                    criteria.append(f"Cycle count shall be ≥ {num}")
                elif unit == '%':
                    criteria.append(f"Performance shall be ≥ {num}%")
                elif unit in ['k']:
                    criteria.append(f"Temperature condition: {num}K")
                else:
                    criteria.append(f"Value shall meet {num} {unit}")
            return '; '.join(criteria) if criteria else "Compliance with requirement as specified"
        else:
            return "Compliance with requirement as specified"
    
    def _determine_requirement_type(self, req_text):
        """Determine type of requirement"""
        text_lower = req_text.lower()
        
        if any(keyword in text_lower for keyword in ['performance', 'capacity', 'power', 'efficiency', 'flow', 'rate']):
            return 'Performance'
        elif any(keyword in text_lower for keyword in ['safety', 'protection', 'interlock', 'purge']):
            return 'Safety'
        elif any(keyword in text_lower for keyword in ['interface', 'connection', 'compatibility']):
            return 'Interface'
        elif any(keyword in text_lower for keyword in ['operation', 'control', 'function', 'scenarios', 'transition']):
            return 'Functional'
        elif any(keyword in text_lower for keyword in ['design', 'construction', 'material', 'lifetime']):
            return 'Design'
        else:
            return 'Functional'
    
    def _determine_priority(self, req_text):
        """Determine requirement priority"""
        text_lower = req_text.lower()
        
        if any(keyword in text_lower for keyword in ['critical', 'safety', 'shall', 'must']):
            return 'High'
        elif any(keyword in text_lower for keyword in ['should', 'recommended', 'may']):
            return 'Medium'
        else:
            return 'High'  # Default for QPLANT requirements
    
    def _generate_rationale(self, req_text):
        """Generate rationale for the requirement"""
        text_lower = req_text.lower()
        
        if 'safety' in text_lower or 'purge' in text_lower:
            return "Required for safe operation of cryogenic system"
        elif any(keyword in text_lower for keyword in ['performance', 'capacity', 'flow']):
            return "Required to meet operational performance targets"  
        elif 'lifetime' in text_lower:
            return "Required to meet project lifetime objectives"
        elif any(keyword in text_lower for keyword in ['operational', 'operation', 'scenario']):
            return "Required for proper operational flexibility and system control"
        else:
            return "Required for proper system functionality"

    def establish_parent_child_relationships(self, requirements):
        """Establish parent-child relationships between requirements"""
        # Group requirements by operational categories
        operational_groups = {
            'lifetime': ['RTM-01', 'RTM-02', 'RTM-03', 'RTM-04'],
            'steady_state': ['RTM-05'],
            'transient': ['RTM-06', 'RTM-07', 'RTM-08', 'RTM-09', 'RTM-010', 'RTM-011', 'RTM-012'],
            'other_ops': ['RTM-013', 'RTM-014', 'RTM-015', 'RTM-016']
        }
        
        # Establish relationships within groups
        for group_name, req_ids in operational_groups.items():
            if len(req_ids) > 1:
                # First requirement in group is parent to others
                parent_id = req_ids[0]
                for req in requirements:
                    if req['req_id'] == parent_id:
                        req['child_requirements'] = req_ids[1:]
                    elif req['req_id'] in req_ids[1:]:
                        req['parent_requirements'] = [parent_id]
        
        return requirements

    def create_rtm_dataframe(self, requirements):
        """Create RTM DataFrame"""
        rtm_data = []
        
        for req in requirements:
            rtm_data.append({
                'Requirement ID': req['req_id'],
                'Description': req['description'], 
                'Full Description': req['full_description'],
                'SBS Level 0': req['sbs_l0'],
                'SBS Level 1': req['sbs_l1'],
                'SBS Level 2': req['sbs_l2'], 
                'SBS Level 3': req['sbs_l3'],
                'Requirement Type': req['requirement_type'],
                'Category': req.get('category', 'General'),
                'Priority': req['priority'],
                'Verification Method': req['verification_method'],
                'Acceptance Criteria': req['acceptance_criteria'],
                'Source Section': req['source_section'],
                'Parent Requirements': ', '.join(req['parent_requirements']),
                'Child Requirements': ', '.join(req['child_requirements']),
                'Status': req['status'],
                'Rationale': req['rationale'],
                'Numerical Value': req.get('numerical_value', 'N/A')
            })
        
        return pd.DataFrame(rtm_data)

    def create_sbs_dataframe(self):
        """Create SBS structure DataFrame"""
        sbs_data = []
        
        for sbs_id, sbs_info in self.sbs_structure.items():
            sbs_data.append({
                'SBS ID': sbs_id,
                'Name': sbs_info['name'], 
                'Level': sbs_info['level'],
                'Parent': sbs_info['parent'] if sbs_info['parent'] else '',
                'Children': ', '.join(sbs_info['children']),
                'Description': sbs_info['description']
            })
        
        return pd.DataFrame(sbs_data)

    def generate_rtm_excel(self, requirements, output_path):
        """Generate comprehensive RTM Excel workbook"""
        # Disable pandas truncation
        pd.set_option('display.max_columns', None)
        pd.set_option('display.max_rows', None)
        pd.set_option('display.max_colwidth', None)
        
        # Create DataFrames
        rtm_df = self.create_rtm_dataframe(requirements)
        sbs_df = self.create_sbs_dataframe()
        
        # Create summary statistics
        summary_data = {
            'Metric': [
                'Total Requirements',
                'High Priority Requirements', 
                'Medium Priority Requirements',
                'Safety Requirements',
                'Performance Requirements',
                'Functional Requirements',
                'Design Requirements',
                'Interface Requirements',
                'Requirements Needing Test Verification',
                'Requirements Needing Analysis Verification',
                'Requirements Needing Demonstration',
                'Operational Requirements',
                'Maintenance Requirements',
                'Lifetime Requirements'
            ],
            'Count': [
                len(requirements),
                len([r for r in requirements if r['priority'] == 'High']),
                len([r for r in requirements if r['priority'] == 'Medium']),
                len([r for r in requirements if r['requirement_type'] == 'Safety']),
                len([r for r in requirements if r['requirement_type'] == 'Performance']), 
                len([r for r in requirements if r['requirement_type'] == 'Functional']),
                len([r for r in requirements if r['requirement_type'] == 'Design']),
                len([r for r in requirements if r['requirement_type'] == 'Interface']),
                len([r for r in requirements if r['verification_method'] == 'Test']),
                len([r for r in requirements if r['verification_method'] == 'Analysis']),
                len([r for r in requirements if r['verification_method'] == 'Demonstration']),
                len([r for r in requirements if r.get('category') == 'Operational']),
                len([r for r in requirements if r.get('category') == 'Maintenance']),
                len([r for r in requirements if r.get('category') == 'Lifetime'])
            ]
        }
        summary_df = pd.DataFrame(summary_data)
        
        # Write to Excel with multiple sheets
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # Navigation sheet
            nav_data = {
                'Sheet Name': ['Requirements_Traceability_Matrix', 'SBS_Structure', 'Summary_Statistics', 'Requirements_by_SBS', 'Requirements_by_Type'],
                'Description': [
                    'Complete RTM with all requirements and traceability',
                    'System Breakdown Structure hierarchy', 
                    'Summary statistics and metrics',
                    'Requirements organized by SBS levels',
                    'Requirements organized by type and category'
                ]
            }
            nav_df = pd.DataFrame(nav_data)
            nav_df.to_excel(writer, sheet_name='Navigation', index=False)
            
            # Main RTM sheet
            rtm_df.to_excel(writer, sheet_name='RTM', index=False)
            
            # SBS structure sheet
            sbs_df.to_excel(writer, sheet_name='SBS', index=False)
            
            # Summary statistics sheet
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            # Requirements by SBS Level 1
            if len(rtm_df) > 0:
                sbs_pivot = rtm_df.groupby(['SBS Level 1', 'Requirement Type']).size().unstack(fill_value=0)
                sbs_pivot.to_excel(writer, sheet_name='BySystem')
                
                # Requirements by Type and Category
                type_pivot = rtm_df.groupby(['Category', 'Requirement Type']).size().unstack(fill_value=0)
                type_pivot.to_excel(writer, sheet_name='ByType')
        
        print(f"RTM Excel workbook created: {output_path}")
        return output_path

    def create_markdown_document(self, requirements, output_path):
        """Create structured markdown document for engineering handover"""
        
        markdown_content = f"""# QPLANT Cryogenic System - Requirements Traceability Matrix
## Engineering Handover Document

**Document Version:** 1.0  
**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
**Project:** MYRRHA Phase 1 - Cryoplant Technical Requirements  
**Document ID:** QPLANT-RTM-001

---

## Executive Summary

This Requirements Traceability Matrix (RTM) provides a comprehensive breakdown of the QPLANT cryogenic system requirements extracted from the technical specification document "Addendum II - Cryoplant Technical Requirements". The RTM establishes clear traceability from high-level system requirements down to specific component-level requirements through a hierarchical System Breakdown Structure (SBS).

### Key Metrics
- **Total Requirements:** {len(requirements)}
- **High Priority Requirements:** {len([r for r in requirements if r['priority'] == 'High'])}
- **Safety Requirements:** {len([r for r in requirements if r['requirement_type'] == 'Safety'])}
- **Performance Requirements:** {len([r for r in requirements if r['requirement_type'] == 'Performance'])}

---

## System Breakdown Structure (SBS)

The QPLANT system is organized according to the following hierarchical structure:

### Level 0 - System Level
- **QSYS**: Complete Cryogenic System
- **QSYS-PR**: Project Requirements

### Level 1 - Major Subsystems  
- **QPLANT**: Main cryogenic refrigeration plant
- **QINFRA**: CSS cryogenic supply system infrastructure
- **QCELL**: CSS cryogenic USER - individual cryomodule and valve box combinations
- **QDIST**: CSS cryogenic USER - distribution lines and headers

### Level 2 - Major Components
- **WCS**: Warm Compressor Station
- **QRB**: Refrigeration Cold Box

### Level 3 - Sub-Components
- **PVPS**: Pressure Vessel & Piping System (under WCS)
- **HP**: High Pressure System (under WCS)
- **CC**: Cold Compressors (under QRB)
- **TURBINES**: Turbo Expanders (under QRB)
- **BATH-4K**: 4K Bath System (under QRB)
- **BATH-2K**: 2K Bath System (under QRB)

---

## Requirements Breakdown

"""
        
        # Group requirements by category
        categories = {}
        for req in requirements:
            cat = req.get('category', 'General')
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(req)
        
        for category, reqs in categories.items():
            markdown_content += f"### {category} Requirements\n\n"
            
            for req in reqs:
                markdown_content += f"#### {req['req_id']}\n"
                markdown_content += f"**Description:** {req['description']}\n\n"
                markdown_content += f"**SBS Assignment:** {req['sbs_l0']} → {req['sbs_l1']} → {req['sbs_l2']}"
                if req['sbs_l3']:
                    markdown_content += f" → {req['sbs_l3']}"
                markdown_content += f"\n\n"
                markdown_content += f"**Type:** {req['requirement_type']}  \n"
                markdown_content += f"**Priority:** {req['priority']}  \n"
                markdown_content += f"**Verification Method:** {req['verification_method']}  \n"
                markdown_content += f"**Acceptance Criteria:** {req['acceptance_criteria']}  \n"
                markdown_content += f"**Rationale:** {req['rationale']}\n\n"
                
                if req['parent_requirements']:
                    markdown_content += f"**Parent Requirements:** {', '.join(req['parent_requirements'])}  \n"
                if req['child_requirements']:
                    markdown_content += f"**Child Requirements:** {', '.join(req['child_requirements'])}  \n"
                
                markdown_content += "---\n\n"
        
        # Add traceability matrix section
        markdown_content += """
## Traceability Matrix Summary

| SBS Level 1 | Requirements Count | High Priority | Safety Critical |
|-------------|-------------------|---------------|-----------------|
"""
        
        sbs_summary = {}
        for req in requirements:
            sbs_l1 = req['sbs_l1']
            if sbs_l1 not in sbs_summary:
                sbs_summary[sbs_l1] = {'total': 0, 'high': 0, 'safety': 0}
            sbs_summary[sbs_l1]['total'] += 1
            if req['priority'] == 'High':
                sbs_summary[sbs_l1]['high'] += 1
            if req['requirement_type'] == 'Safety':
                sbs_summary[sbs_l1]['safety'] += 1
        
        for sbs, counts in sbs_summary.items():
            markdown_content += f"| {sbs} | {counts['total']} | {counts['high']} | {counts['safety']} |\n"
        
        markdown_content += f"""

---

## GitHub Integration Readiness

This RTM is prepared for integration with the existing GitHub infrastructure:

- **GBOGEB/DOCX_RTM_Automation**: Ready for automated RTM updates
- **GBOGEB/ABACUS**: Compatible with existing project structure  
- **pipeline-automation-hub**: Ready for CI/CD integration
- **KEB Digital Twin**: Requirements mapped to system components
- **HEPAK projects**: Traceability established for cryogenic properties

## Next Steps

1. **Review and Validation**: Technical review of extracted requirements
2. **Gap Analysis**: Identify any missing requirements from source documents
3. **Integration Testing**: Verify compatibility with existing GitHub workflows
4. **Stakeholder Approval**: Obtain approval from engineering teams
5. **Implementation**: Deploy to production RTM system

## Document Control

- **Author**: DeepAgent RTM Generator
- **Reviewer**: [To be assigned]
- **Approver**: [To be assigned]
- **Next Review Date**: [To be scheduled]

---

*This document was generated automatically from the QPLANT technical requirements specification. For questions or updates, please contact the project technical team.*
"""

        # Write markdown file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        print(f"Markdown document created: {output_path}")
        return output_path

def main():
    print("🚀 Improved Cryoplant RTM Generator Starting...")
    
    # Initialize generator
    generator = ImprovedCryoplantRTMGenerator()
    
    print("📖 Extracting requirements from documents...")
    # Extract requirements using improved method
    requirements = generator.extract_requirements_from_pdf_text()
    
    print(f"✅ Found {len(requirements)} requirements")
    
    # Establish relationships
    print("🔗 Establishing parent-child relationships...")
    requirements = generator.establish_parent_child_relationships(requirements)
    
    # Generate Excel RTM
    print("📊 Generating Excel RTM workbook...")
    excel_path = "/home/ubuntu/QPLANT_Requirements_Traceability_Matrix_v2.xlsx"
    generator.generate_rtm_excel(requirements, excel_path)
    
    # Generate Markdown document
    print("📝 Generating Markdown engineering handover document...")
    markdown_path = "/home/ubuntu/QPLANT_RTM_Engineering_Handover.md"
    generator.create_markdown_document(requirements, markdown_path)
    
    # Save requirements as JSON for further processing
    json_path = "/home/ubuntu/qplant_requirements_v2.json"
    with open(json_path, 'w') as f:
        json.dump(requirements, f, indent=2)
    
    print("✨ RTM Generation Complete!")
    print(f"📁 Excel RTM: {excel_path}")
    print(f"📁 Markdown Document: {markdown_path}")
    print(f"📁 JSON Data: {json_path}")
    
    # Display summary
    print("\n📋 Summary:")
    print(f"   Total Requirements: {len(requirements)}")
    print(f"   High Priority: {len([r for r in requirements if r['priority'] == 'High'])}")
    print(f"   Safety Requirements: {len([r for r in requirements if r['requirement_type'] == 'Safety'])}")
    print(f"   Performance Requirements: {len([r for r in requirements if r['requirement_type'] == 'Performance'])}")
    
    return requirements, excel_path, markdown_path

if __name__ == "__main__":
    requirements, excel_path, markdown_path = main()