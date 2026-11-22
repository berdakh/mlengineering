# delay_ignored
Counts every prediction in the window as labelled, ignoring that labels arrive late. This is the most
common planning error in delayed-label systems. Caught by: test_labels_available_respects_delay,
test_labels_available_zero_when_window_shorter_than_delay.
