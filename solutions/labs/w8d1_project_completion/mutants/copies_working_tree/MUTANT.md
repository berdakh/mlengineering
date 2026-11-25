Copies the working directory instead of cloning. Untracked files (here: data/ that is git-ignored) leak into the audit, so a project that cannot be reproduced from git passes.
