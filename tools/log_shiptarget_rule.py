# 2026-09-09 (Lloyd): "please make sure the Sim that is shipped is the sandbox version and we don't ship to the one
# on the proposal page unless I say so". Writes the rule into AGENTS.md's agent rules. Idempotent.
AG = 'AGENTS.md'
old = """- Writes that a client would see (a live stream on a hall, a commit, a push) need the owner's word
  first.
"""
new = old + """- **WHAT THIS REPO SHIPS IS THE SANDBOX, NEVER THE PROPOSAL PAGE** (Lloyd, 2026-09-09: "make sure
  the Sim that is shipped is the sandbox version and we don't ship to the one on the proposal page
  unless I say so"). `git push origin main` publishes GitHub Pages at
  https://lotron-electrical.github.io/ngv-hall-model/, and that page is the sandbox: its header
  reads "Sandbox" over "Gandel Hall Sim" (index.html, the `<header>` line). Checked 2026-09-09: the
  proposal page https://lotronelectrical.com/pages/ngv-gandel-hall carries NO iframe and NO link to
  the sim, and nothing in this repo can write to Shopify (no workflow, no deploy script; the only
  file that names the store is tools/live-preview.js, and that name is an ELM show file). So a push
  from here cannot reach the proposal. Putting the sim on the proposal page, or changing what the
  proposal embeds, is a separate act on the Shopify side and needs Lloyd to ask for it by name.
  Before reporting anything live, say WHICH page: the sandbox.
"""
s = open(AG, encoding='utf-8').read()
if 'WHAT THIS REPO SHIPS IS THE SANDBOX' not in s:
    assert s.count(old) == 1
    open(AG, 'w', encoding='utf-8', newline='\n').write(s.replace(old, new))
print('rule written')
