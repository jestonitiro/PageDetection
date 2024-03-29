import xml.etree.ElementTree as ET
import json

from object import Object
from number_helper import NumberHelper
from scanned_data import ScannedData


class Book:
    def __init__(self, xml_filename):
        tree = ET.parse(xml_filename)
        root = tree.getroot()
        self.object_list = []
        self.blank_gap_dictionary = {}
        self.last_blank_start = 0
        for object_element in root.iter('OBJECT'):
            object_ = Object(object_element)
            object_.extract_words()
            object_.extract_possible_page_numbers()
            self.object_list.append(object_)
        self.__perform_temporary_prediction()
        self.__perform_fillup_gaps_arabic()
        self.__perform_fillup_roman_numerals()

    # Perform temporary prediction, filling up objects (predicted_page_temp and
    # expected_next_printed_page).
    def __perform_temporary_prediction(self):
        blank_start = -1
        blank_end = -1
        for i in range(0, len(self.object_list)-1):
            self.object_list[i].predict_page_printed_number(self.object_list)
            if not self.object_list[i].predicted_page_temp:
                if blank_start == -1:
                    blank_start = i
                blank_end = i
            else:
                if blank_start != -1:
                    self.blank_gap_dictionary[blank_start] = blank_end
                    blank_start = -1
                    blank_end = -1
        if blank_start != -1:
            self.blank_gap_dictionary[blank_start] = blank_end + 1

    def __perform_fillup_gaps_arabic(self):
        matched_keys = []
        for key in self.blank_gap_dictionary:
            if key > 0:
                blank_start = key
                blank_end = self.blank_gap_dictionary[key]
                start_candidate = self.object_list[blank_start].candidate_printed_page
                end_candidate = self.object_list[blank_end].candidate_printed_page
                if start_candidate.isnumeric() and end_candidate.isnumeric():
                    if str(int(start_candidate)-1) == self.object_list[blank_start-1].predicted_page_temp \
                            and str(int(end_candidate)+1) == self.object_list[blank_end+1].predicted_page_temp:
                        for i in range(blank_start, blank_end + 1):
                            self.object_list[i].predicted_page_temp = self.object_list[i].candidate_printed_page
                            self.object_list[i].sure_prediction = True
                        matched_keys.append(key)

        # Remove successfully matched
        for key in matched_keys:
            self.blank_gap_dictionary.pop(key)

        # fill blank pages copy candidate page if match with last printed temp page
        objects_ = self.get_empty_predicted_temp_with_candidates()
        self.fill_up_empty_temp_pages_with_candidate_page(objects_)
        objects_ = self.get_empty_predicted_temp()
        self.fill_up_empty_temp_pages(objects_)

        for key in self.blank_gap_dictionary:
            blank_start = key
            blank_end = self.blank_gap_dictionary[key]
            # This is the topmost blanks
            if blank_start == 0 and blank_end < len(self.object_list)-1:
                next_object = self.object_list[blank_end + 1]
                if next_object.predicted_page_temp.isnumeric():
                    current_page = int(next_object.predicted_page_temp) - 1
                    if current_page >= 1:
                        for i in range(blank_end, blank_start-1, -1):
                            self.object_list[i].predicted_page_temp = str(current_page)
                            current_page -= 1
                            if current_page < 1:
                                break
            # This is the last blanks to the end.
            if blank_start > 0 and blank_end == len(self.object_list)-1:
                self.last_blank_start = blank_start
                previous_object = self.object_list[blank_start - 1]
                if previous_object.expected_next_printed_page in self.object_list[key].texts():
                    self.object_list[key].predicted_page_temp = previous_object.expected_next_printed_page

            # Resequence
            for object_ in self.object_list:
                prev_object = self.get_object_object_by_leafnumber(object_.leaf_number-1)
                if prev_object is None:
                    continue
                if not prev_object.predicted_page_temp.isnumeric() or not object_.predicted_page_temp.isnumeric():
                    continue

                page = int(object_.predicted_page_temp)
                prev_page = int(prev_object.predicted_page_temp)
                if page < prev_page:
                    self.object_list[object_.leaf_number-1].predicted_page_temp = str(prev_page + 1)



    def __perform_fillup_roman_numerals(self):
        blank_end = 0
        roman_count = 0
        for object_ in self.object_list:
            if not object_.predicted_page_temp:
                blank_end += 1
                for text in object_.texts():
                    if NumberHelper.is_valid_roman_numeral(text):
                        roman_count += 1
                        break
            else:
                break
        # Make sure that there are at least 3 roman numeral appearnaces.
        if roman_count >= 3:
            page = 0
            max_matched_count = 0
            max_matched_start = 0
            while page < blank_end:
                page += 1
                match_count = 0
                for i in range(page, blank_end):
                    roman_prediction = NumberHelper.int_to_roman((i - page) + 1).lower()
                    object_ = self.object_list[i]
                    if roman_prediction in object_.texts_lower():
                        match_count += 1
                if match_count > max_matched_count:
                    max_matched_count = match_count
                    max_matched_start = page
                if blank_end-page < max_matched_count:
                    break

            if max_matched_count >= 3:
                for page in range(max_matched_start, blank_end):
                    roman_prediction = NumberHelper.int_to_roman((page - max_matched_start) + 1).lower()
                    self.object_list[page].predicted_page_temp = roman_prediction


    # check if page exists
    def is_page_exists(self, start, page):
        prediction_exist = False
        for x in range(start, len(self.object_list) - 1):
            if self.object_list[x].predicted_page_temp == str(page):
                prediction_exist = True
                break
        return prediction_exist

    # print temp page that are empty
    def fill_up_empty_temp_pages_with_candidate_page(self, objects_:[]):
        for object_ in objects_:
            blank_start = object_.leaf_number
            if object_.candidate_printed_page is None:
                continue

            if object_.candidate_printed_page.isnumeric():
                current_page = int(object_.candidate_printed_page)
                total_blanks = 0
                last_object = None
                last_prediction_found = False

                if current_page >= 1:
                    for i in range(blank_start - 1, 0, -1):
                        last_object = self.get_object_object_by_leafnumber(i)
                        if last_object.predicted_page_temp is not None:

                            if last_object.predicted_page_temp != '':
                                total_blanks += 1

                            if last_object.predicted_page_temp != '' and last_object.sure_prediction:
                                last_prediction_found = True
                                break

                    if last_prediction_found:
                        last_page = int(last_object.predicted_page_temp)
                        if current_page - last_page == total_blanks:
                            if not self.is_page_exists(blank_start, current_page):
                                self.object_list[blank_start - 1].predicted_page_temp = str(current_page)

    def fill_up_empty_temp_pages(self, objects_:[]):
        for object_ in objects_:
            total_pages = 0
            last_object = None
            for i in range(object_.leaf_number - 1, 0, -1):
                last_object = self.get_object_object_by_leafnumber(i)
                if last_object.predicted_page_temp is not None:
                    if last_object.predicted_page_temp != '':
                        total_pages += 1
                        if last_object.predicted_page_temp != '' and last_object.sure_prediction:
                            break

            if last_object is not None and total_pages != 0:
                current_page = str(int(last_object.predicted_page_temp) + total_pages)
                if not self.is_page_exists(object_.leaf_number, current_page):
                    self.object_list[object_.leaf_number-1].predicted_page_temp = current_page

    # filter dictionary that are not empty
    def get_dictionary_not_empty(self, dic_list: {}):
        for key in dic_list:
            if dic_list[key] != '':
                yield key

    # get previous temp object
    def get_previous_object_with_page(self, start):
        for i in range(start - 1, 0, -1):
            last_object = self.get_object_object_by_leafnumber(i)
            if last_object.predicted_page_temp is not None:
                if last_object.predicted_page_temp != '' and last_object.sure_prediction:
                    return last_object
                    break
        return None
    # get previous temp object
    def get_last_object_with_page(self, start):
        for i in range(start, len(self.object_list) - 1):
            last_object = self.get_object_object_by_leafnumber(i)
            if last_object.predicted_page_temp is not None:
               if last_object.predicted_page_temp != '' and last_object.sure_prediction:
                  return last_object
                  break
        return None

    # filter list to get empty temp print page with candidates
    def get_empty_predicted_temp_with_candidates(self):
        for obj in self.object_list:
            if obj.predicted_page_temp == '' and obj.candidate_printed_page != '':
                yield obj

    # filter list to get empty temp print page
    def get_empty_predicted_temp(self):
        for obj in self.object_list:
            if obj.predicted_page_temp == '' or obj.predicted_page_temp is None:
               yield obj

    # get page value by leaf number
    def get_object_pagevalue_by_leafnumber(self, leaf_no):
        for object_ in self.object_list:
            if object_.leaf_number == leaf_no:
                return object_.predicted_page_temp

        return ''
    # get object by leaf number
    def get_object_object_by_leafnumber(self, leaf_no):
        for object_ in self.object_list:
            if object_.leaf_number == leaf_no:
                return object_

        return None

    def generate_json(self, item, json_filename, scan_data: ScannedData):
        json_pages = []
        expected_num = 0
        is_num_started = False
        check_leaf = []         # This is blank in between numbers and non-sequence numbers.
        for object_ in self.object_list:
            if object_.predicted_page_temp.isnumeric():
                is_num_started = True
                num = int(object_.predicted_page_temp)
                if num != expected_num + 1:
                    check_leaf.append(object_.leaf_number)
                expected_num = num
            if not object_.predicted_page_temp and is_num_started and int(object_.leaf_number) < self.last_blank_start:
                check_leaf.append(object_.leaf_number)
            json_pages.append(
                json.loads(json.dumps({"leafNum": object_.leaf_number, "pageNumber": object_.predicted_page_temp})))
            # print(object_.leaf_number,object_.texts())

        accuracy = 100.00
        if len(check_leaf) > 0:
            accuracy = (1 - (len(check_leaf) / len(self.object_list))) * 100

        mis_matched = 0
        total_scandata = 0;
        scanned_accuracy = 100.00
        scanned_mismatches = []
        for key in self.get_dictionary_not_empty(dic_list=scan_data.leaf_page_dictionary):
            output_val = self.get_object_pagevalue_by_leafnumber(int(key))
            if scan_data.leaf_page_dictionary[key] == output_val:
                mis_matched += 1
            else:
                scanned_mismatches.append("leafno["+ str(key) +"] scandata \"" + scan_data.leaf_page_dictionary[key] + "\" output\"" + output_val + "\"")

            total_scandata += 1

        scanned_accuracy = (mis_matched / total_scandata) * 100
        json_data = {
            "identifier": item,
            "confidence": accuracy,
            "leafForChecking": check_leaf,
            # "scannedDataComparison": scanned_accuracy,
            "scandataOutputMismatched": scanned_mismatches,
            "pages": json_pages
        }
        with open(json_filename, 'w') as f:
            json.dump(json_data, f, ensure_ascii=False)

        print(f"Successfully saved as [{json_filename}] with accuracy of {accuracy}%.")
