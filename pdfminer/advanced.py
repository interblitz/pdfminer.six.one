from typing import List, Iterator
from .utils import Plane, Rect
from enum import Enum


class CountableDictHelper:

    @staticmethod
    def put_keys(d: "Dict", keys: "List"):
        for key in keys:
            d[key] = d.get(key, 0) + 1

    @staticmethod
    def get_max_key(d: "Dict", default_key=None):
        max_value = 0
        max_key = default_key
        for key in d:
            if d.get(key) > max_value:
                max_value = d.get(key)
                max_key = key
        return max_key


class Iterators:

    @staticmethod
    def neighbor_iterator(neighbors: List["LTComponent"]) -> Iterator["LTComponent, LTComponent"]:
        prev_obj = None
        for obj in neighbors:
            if prev_obj is not None:
                yield prev_obj, obj
            prev_obj = obj


class NeighborMatcher:
    """
    Interface for advanced neighbors controlling
    """

    def clear(self):
        pass

    def init(self, text_line: 'LTTextLine'):
        pass

    def matched(self, prev_text_line: 'LTTextLine', text_line: 'LTTextLine') -> bool:
        pass


class Alignment(Enum):
    No = 0
    Left = 1
    Right = 2
    Center = 3


class TextBoxesHelper:

    @staticmethod
    def calculate_horizontal_attributes(textboxes: List["LTComponent"], otherobjs: List["LTComponent"], bbox: Rect):
        """Detects alignments, horizontal paddings and margins"""
        """xxxxxxxxxxxx                                       """
        """xxx<--------><-------------><------------->yyy     """
        """    padding   margin of xxx  margin of yyy         """

        plane = Plane(bbox)
        plane.extend(textboxes)

        """
        Looking for textboxes having same alignment
        and grouping them into groups
        then assigning alignment, and calculate paddings 
        """

        processed_textboxes = []
        for textbox in textboxes:
            TextBoxesHelper.attach_horizontal_attributes(textbox)

            if '(RUB)' in textbox.get_text():
                a = 1

            if textbox in processed_textboxes:
                continue

            tolerance = TextBoxesHelper.get_line_height(textbox)

            # Looking for objects below self to bottom
            objs = plane.find((textbox.x0, 0, textbox.x1, textbox.y1))
            v_sorted_objs = sorted(objs, key=lambda obj: obj.y0, reverse=True)

            h_alignment = Alignment.No
            # Group can have several aligments, at the final step we should select one
            group_h_alignments = {}
            min_x0 = 0
            max_x1 = 0
            similar_objs = []
            for obj in v_sorted_objs:
                if obj != textbox:
                    v_distance = textbox.vdistance(obj)
                    is_same_height = TextBoxesHelper._is_same_height_as(textbox, obj, tolerance * .2)
                    if v_distance > 0 and is_same_height:
                        h_alignments = []
                        if TextBoxesHelper._is_left_aligned_with(textbox, obj, tolerance=tolerance):
                            h_alignments.append(Alignment.Left)
                        if TextBoxesHelper._is_right_aligned_with(textbox, obj, tolerance=tolerance):
                            h_alignments.append(Alignment.Right)
                        if TextBoxesHelper._is_centrally_aligned_with(textbox, obj, tolerance=tolerance):
                            h_alignments.append(Alignment.Center)
                        if len(h_alignments) > 0:
                            CountableDictHelper.put_keys(group_h_alignments, h_alignments)
                            min_x0 = min(min_x0, obj.x0)
                            max_x1 = max(max_x1, obj.x1)
                            similar_objs.append(obj)
                        else:
                            break
                    else:
                        break
                else:
                    min_x0 = obj.x0
                    max_x1 = obj.x1
                    similar_objs.append(obj)

            # Setting alignments, padding
            h_alignment = CountableDictHelper.get_max_key(group_h_alignments, Alignment.Left)
            for obj in similar_objs:
                TextBoxesHelper.attach_horizontal_attributes(obj)
                processed_textboxes.append(obj)

                obj.h_alignment = h_alignment
                padding = max(0, (max_x1 - min_x0) - obj.width)
                if textbox.h_alignment == Alignment.Left:
                    obj.padding_right = max(obj.padding_right, padding)
                elif textbox.h_alignment == Alignment.Right:
                    obj.padding_left = max(obj.padding_left, padding)
                elif textbox.h_alignment == Alignment.Center:
                    obj.padding_left = max(obj.padding_left, padding / 2)
                    obj.padding_right = max(obj.padding_right, padding / 2)

        # Setting margins - based on other object intersections
        plane.extend(otherobjs)
        for textbox in textboxes:
            # Looking for objects right of the textbox
            objects_right_of = plane.find((textbox.x1, textbox.y0, bbox[2], textbox.y1))
            objects_starts_right_of = [
                obj
                for obj in objects_right_of
                if (obj.x0 >= textbox.x1)
            ]
            h_sorted_objs = sorted(objects_starts_right_of, key=lambda obj: obj.x0, reverse=False)
            if len(h_sorted_objs) > 0:
                closed_object = h_sorted_objs[0]
                distance = closed_object.x0 - textbox.x1
                ### For text objects divide distance between neighbors
                if closed_object.__class__.__name__ == "LTTextBoxHorizontal":
                    objects_padding = textbox.padding_right + closed_object.padding_left
                    if objects_padding < distance:
                        margin = (distance - objects_padding) / 2
                        closed_object.margin_left = margin
                        textbox.margin_right = margin
                    else:
                        padding_correction = (objects_padding - distance) / 2
                        if closed_object.padding_left >= padding_correction and textbox.padding_right >= padding_correction:
                            closed_object.padding_left = closed_object.padding_left - padding_correction
                            textbox.padding_right = textbox.padding_right - padding_correction
                        elif closed_object.padding_left >= padding_correction:
                            delta = padding_correction - textbox.padding_right
                            textbox.padding_right = 0
                            closed_object.padding_left = max(0, closed_object.padding_left - padding_correction - delta)
                        else:
                            delta = padding_correction - closed_object.padding_left
                            closed_object.padding_left = 0
                            textbox.padding_right = max(0, textbox.padding_right - padding_correction - delta)
                    continue
            else:
                distance = bbox[2] - textbox.x1
            if textbox.padding_right > distance:
                textbox.padding_right = distance
            else:
                textbox.margin_right = distance - textbox.padding_right

    @staticmethod
    def get_line_height(textbox: "LTTextBoxHorizontal") -> float:
        """
        Returns max line height in the textbox
        """
        line_height = 0
        for line in textbox:
            line_height = max(line_height, line.height)
        return line_height

    @staticmethod
    def _is_left_aligned_with(self, other: "LTComponent", tolerance: float = 0) -> bool:
        """
        Whether the left-hand edge of `other` is within `tolerance`.
        """
        return abs(other.x0 - self.x0) <= tolerance

    @staticmethod
    def _is_right_aligned_with(self, other: "LTComponent", tolerance: float = 0) -> bool:
        """
        Whether the right-hand edge of `other` is within `tolerance`.
        """
        return abs(other.x1 - self.x1) <= tolerance

    @staticmethod
    def _is_centrally_aligned_with(
            self, other: "LTComponent", tolerance: float = 0
    ) -> bool:
        """
        Whether the horizontal center of `other` is within `tolerance`.
        """
        return abs((other.x0 + other.x1) / 2 - (self.x0 + self.x1) / 2) <= tolerance

    @staticmethod
    def _is_same_height_as(self, other: "LTComponent", tolerance: float = 0) -> bool:
        return abs(other.height - self.height) <= tolerance

    @staticmethod
    def attach_horizontal_attributes(textbox: "LTTextBoxHorizontal"):
        if getattr(textbox, "h_alignment", 0) == 0:
            setattr(textbox, "h_alignment", Alignment.No)
        if getattr(textbox, "padding_left", -1) == -1:
            setattr(textbox, "padding_left", 0)
        if getattr(textbox, "padding_right", -1) == -1:
            setattr(textbox, "padding_right", 0)
        if getattr(textbox, "margin_left", -1) == -1:
            setattr(textbox, "margin_left", 0)
        if getattr(textbox, "margin_right", -1) == -1:
            setattr(textbox, "margin_right", 0)
