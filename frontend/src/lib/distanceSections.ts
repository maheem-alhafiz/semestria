import type { SectionGroup, SectionOption } from "@/types/api";

// Aurora labels distance/online sections with a "D0X" section number
// (e.g. "D01"). Confirmed from real data (MATH 1500): these land as their
// OWN separate group (link_group_id null, standalone) rather than being
// merged into the same group as the in-person lecture/tutorial sections
// -- Aurora doesn't link them to the real sections at all. That's why
// detection has to work at the GROUP level, not just flagging individual
// options: a group qualifies as "distance" only if every option in it is
// a distance section.
export function isDistanceOption(option: SectionOption): boolean {
  return /^D\d+/i.test(option.section_number);
}

export function isDistanceGroup(group: SectionGroup): boolean {
  return group.slots.every(
    (slot) => slot.options.length > 0 && slot.options.every(isDistanceOption),
  );
}
