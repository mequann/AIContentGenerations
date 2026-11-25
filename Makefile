# Thin wrapper — every target maps to `python -m pipeline <cmd>` so Windows users
# without make can run the same thing directly.
PY ?= python

.PHONY: setup smoke validate script narration radio references keyframes shots music assemble film demo report test clean

setup:      ; $(PY) -m pip install -r requirements.txt
smoke:      ; $(PY) -m pipeline smoke
validate:   ; $(PY) -m pipeline validate
script:     ; $(PY) -m pipeline script --story story/story.md
narration:  ; $(PY) -m pipeline narration
radio:      ; $(PY) -m pipeline radio
references: ; $(PY) -m pipeline references
keyframes:  ; $(PY) -m pipeline keyframes
shots:      ; $(PY) -m pipeline shots
music:      ; $(PY) -m pipeline music
assemble:   ; $(PY) -m pipeline assemble
film:       ; $(PY) -m pipeline film
demo:       ; $(PY) -m pipeline film --mock --storyboard tests/fixtures/demo_storyboard.json --out outputs_demo
report:     ; $(PY) -m pipeline report
test:       ; $(PY) -m pytest -q
clean:      ; $(PY) -m pipeline clean
