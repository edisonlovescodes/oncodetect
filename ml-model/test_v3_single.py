import os
import pydicom
import xml.etree.ElementTree as ET
import cv2
import numpy as np

RAW_DATA_PATH = 'raw_data/LIDC-IDRI'
CROP_SIZE = 64

# Test on the patient we know has 26 nodules
test_patient = 'LIDC-IDRI-0049'
patient_folder = os.path.join(RAW_DATA_PATH, test_patient)

print(f"Testing on: {test_patient}")
print("="*60)

# Build master dictionary
all_slices = {}
xml_path = None

print("Scanning all folders for DICOM and XML files...")
for root, dirs, files in os.walk(patient_folder):
    for f in files:
        if f.endswith('.xml'):
            xml_path = os.path.join(root, f)
            print(f"Found XML: {xml_path}")
    
    for f in files:
        if f.endswith('.dcm'):
            try:
                dcm_path = os.path.join(root, f)
                ds = pydicom.dcmread(dcm_path)
                if hasattr(ds, 'SOPInstanceUID'):
                    all_slices[ds.SOPInstanceUID] = ds.pixel_array
            except:
                pass

print(f"\nTotal DICOM slices loaded: {len(all_slices)}")

if xml_path:
    # Parse XML
    tree = ET.parse(xml_path)
    xmlroot = tree.getroot()
    ns = {'ns': 'http://www.nih.gov'}
    
    nodule_count = 0
    matched = 0
    
    for reading_session in xmlroot.findall('ns:readingSession', ns):
        for unblinded_read in reading_session.findall('ns:unblindedReadNodule', ns):
            roi = unblinded_read.find('ns:roi', ns)
            if roi is None:
                continue
            
            image_uid_elem = roi.find('ns:imageSOP_UID', ns)
            if image_uid_elem is None:
                continue
            
            characteristics = unblinded_read.find('ns:characteristics', ns)
            if characteristics is None:
                continue
            
            malignancy = characteristics.find('ns:malignancy', ns)
            if malignancy is None or malignancy.text is None:
                continue
            
            nodule_count += 1
            
            # Check if we can match this nodule
            if image_uid_elem.text in all_slices:
                matched += 1
            else:
                print(f"  ❌ Nodule {nodule_count}: UID not found in DICOM files")
    
    print(f"\nTotal nodules in XML: {nodule_count}")
    print(f"Successfully matched: {matched}")
    print(f"Match rate: {matched/nodule_count*100:.1f}%")
else:
    print("ERROR: No XML file found!")
