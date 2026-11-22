# Hint 1 - concept (w6d2)

**Lab.** List every input of the build that is not a file in your repository: the base image and the
package index. For each, ask "what does this name point to, and can it point somewhere else next
month?". A tag and a range can; a digest and an `==` + hash cannot. The lock is the *output* of a
resolver run once, kept in Git; the image build only ever *reads* it.

A multi-stage build is "build here, ship there": everything that only building needs stays in a stage
whose filesystem is thrown away. Ask which single directory the runtime needs from the builder.

The smoke test has three possible answers, not two: the service never became ready, it answered
wrongly, or it answered correctly. Design the control flow around those three.

**Challenge.** The repository did not change, the expected scores did not change, the input did not
change. So something *outside* the repository changed between the two builds. Look at what
`build.sh` installs today and compare it with what was installed two weeks ago.
