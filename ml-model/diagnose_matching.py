import os
import pydicom
import xml.etree.ElementTree as ET

RAW_DATA_PATH = 'raw_data/LIDC-IDRI'

# Pick a patient we know has many nodules
test_patient = 'LIDC-IDRI-0049'  # Should have 26 nodules
patient_path = os.path.join(RAW_DATA_PATH, test_patient)

print(f"Diagnosing: {test_patient}")
print("="*60)

# Find scan folder with DICOM files
for root, dirs, files in os.walk(patient_path):
    dcm_files = [f for f in files if f.endswith('.dcm')]
    xml_files = [f for f in files if f.endswith('.xml')]
    
    if dcm_files and xml_files:
        print(f"\nFound scan folder with {len(dcm_files)} DICOM files")
        
        # Parse XML
        xml_path = os.path.join(root, xml_files[0])
        tree = ET.parse(xml_path)
        xmlroot = tree.getroot()
        ns = {'ns': 'http://www.nih.gov'}
        
        # Get all UIDs from XML
        xml_uids = set()
        for roi in xmlroot.findall('.//ns:roi', ns):
            uid_elem = roi.find('ns:imageSOP_UID', ns)
            if uid_elem is not None:
                xml_uids.add(uid_elem.text)
        
        print(f"XML references {len(xml_uids)} unique slice UIDs")
        
        # Get all UIDs from DICOM files
        dcm_uids = set()
        for dcm_file in dcm_files[:50]:  # Sample first 50
            try:
                ds = pydicom.dcmread(os.path.join(root, dcm_file))
                if hasattr(ds, 'SOPInstanceUID'):
                    dcm_uids.add(ds.SOPInstanceUID)
            except:
                pass
        
        print(f"DICOM files contain {len(dcm_uids)} unique UIDs (sampled 50 files)")
        
        # Check overlap
        matches = xml_uids.intersection(dcm_uids)
        print(f"\nMatches found: {len(matches)}")
        print(f"Match rate: {len(matches)/len(xml_uids)*100:.1f}%")
        
        if len(matches) == 0:
            print("\n⚠️  NO MATCHES! This is the problem.")
            print("\nSample XML UID:", list(xml_uids)[:1])
            print("Sample DICOM UID:", list(dcm_uids)[:1])
        
        break
