import xml.etree.ElementTree as ET


class ScannedData:
    def __init__(self, scandataxml: str):
        self.leaf_page_dictionary = {}
        self.leaf_page_dictionary1 = {}
        self.leaf_page_dictionary2 = {}
        tree = ET.parse(scandataxml)
        for page_elem in tree.findall('.//pageData/page'):
            leaf_num_value = int(page_elem.attrib["leafNum"])
            page_num_value = ""
            page_num_elem = page_elem.find("./pageNumber")
            if page_num_elem is not None:
                page_num_value = page_num_elem.text

            if leaf_num_value not in self.leaf_page_dictionary:
                self.leaf_page_dictionary[leaf_num_value] = page_num_value
