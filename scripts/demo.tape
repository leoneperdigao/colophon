# VHS tape — records the live terminal demo into docs/assets/demo.gif.
# Prereqs: a running stack (`make up-d`) and VHS (https://github.com/charmbracelet/vhs).
# Generate via:  make media   (or:  vhs scripts/demo.tape)

Output docs/assets/demo.gif

Set Shell "bash"
Set FontSize 17
Set Width 1180
Set Height 860
Set Padding 26
Set Theme "Catppuccin Mocha"
Set TypingSpeed 35ms
Set PlaybackSpeed 1.0

Type "uv run python scripts/demo_flow.py"
Sleep 600ms
Enter
Sleep 16s
