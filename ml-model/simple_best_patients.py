import os
import xml.etree.ElementTree as ET
from collections import defaultdict

RAW_DATA_PATH = 'raw_data/LIDC-IDRI'

patient_nodule_counts = defaultdict(int)

# Walk through all patient folders
for patient_folder in os.listdir(RAW_DATA_PATH):
    if not patient_folder.startswith('LIDC-IDRI'):
        continue
    
    patient_path = os.path.join(RAW_DATA_PATH, patient_folder)
    
    # Find XML files
    for root, dirs, files in os.walk(patient_path):
        for file in files:
            if file.endswith('.xml'):
                xml_path = os.path.join(root, file)
                try:
                    tree = ET.parse(xml_path)
                    xmlroot = tree.getroot()
                    ns = {'ns': 'http://www.nih.gov'}
                    
                    # Count nodules with clear malignancy scores
                    for reading in xmlroot.findall('.//ns:unblindedReadNodule', ns):
                        chars = reading.find('ns:characteristics', ns)
                        if chars is not None:
                            malig = chars.find('ns:malignancy', ns)
                            if malig is not None and malig.text not in ['3', None]:
                                patient_nodule_counts[patient_folder] += 1
                except:
                    pass

# Sort and display
sorted_patients = sorted(patient_nodule_counts.items(), key=lambda x: x[1], reverse=True)

print("\nPatients ranked by usable nodules:")
print("-" * 50)
for pid, count in sorted_patients[:50]:
    print(f"{pid}: {count} nodules")
