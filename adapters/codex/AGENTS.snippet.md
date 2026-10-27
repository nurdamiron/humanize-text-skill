## Writing style for human-facing text

When writing prose for people (replies, docs, commit messages, PR descriptions, emails), follow `skills/humanize-text/SKILL.md`:
state the main point in the first sentence, use concrete facts instead of evaluations, no closing recap, no chat wrappers
("Great question", "Hope this helps"), avoid em dashes and unneeded markdown, avoid "not just X but Y" and reflexive triplets.
For drafts over ~150 words run `python3 skills/humanize-text/scripts/humanize_check.py check <file>` and fix what it finds;
after editing run `... compare <before> <after>` to confirm no numbers, dates or links were lost or added.
