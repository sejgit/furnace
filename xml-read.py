#!/usr/bin/env python3

import xml.etree.ElementTree as ET


def main():
    tree = ET.parse('status.xml')
    root = tree.getroot()

    features = ['name', 'currentActivity', 'rt', 'rh', 'hold']

    for item in features:
        # find the first 'item' object
        for num, zone in enumerate(root.iter(item)):
            if zone.text and num == 0:
                print("Zone {}: {} = {}".format(num + 1, item, zone.text))

    # for child in root:
    #     print(child.tag, child.text)
    #     if child.tag == 'zones':
    #         for zone in child:
    #             print(zone.attrib)


if __name__ == '__main__':
    main()
    exit()

#
# Done
#
# # # end of script
