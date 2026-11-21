# Hint 1 (concept): what to look for

No locations, only kinds of fault. The notebook contains at least one of each.

1. **An identifier derived from position.** Whenever a label for a thing is computed from *where it
   happened to be in a list*, ask what determined the order of the list.
2. **A cleaning step that removes rows without saying how many.** Any line that can drop rows should
   make you compare the count before and after, and ask *which* rows went.
3. **An operation over the whole table that only makes sense within a group.** Sorting, differencing
   and indexing all have a "per recording" and an "over everything" version. In your EEG work the
   same mistake is a filter or a baseline computed across a concatenation of sessions.
4. **A name that means different things in different cells.** Find a variable that is assigned in
   more than one cell and read every use of it.
5. **Meaning assigned by column position.** It works until the file changes.

For the refactor itself: the smallest function is "one file in, one clean frame out". Everything
else is built from it. Write its test on a file you construct in a temporary directory, and make the
constructed file awkward on purpose.

For the challenge: what does "consecutive" mean when the table contains many recordings?
