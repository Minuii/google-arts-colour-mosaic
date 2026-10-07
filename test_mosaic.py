import os
from playwright.sync_api import sync_playwright
from PIL import Image

here = os.path.abspath(".")
test = os.path.join(here, "mosaic", "_test.png")
Image.linear_gradient("L").convert("RGB").resize((400, 300)).save(test)

with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    pg = b.new_page(viewport={"width": 1200, "height": 900})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto("file:///" + here.replace("\\", "/") + "/mosaic/index.html")
    pg.set_input_files("#file", test)
    pg.wait_for_function("document.getElementById('msg').textContent.includes('tiles')", timeout=60000)
    disp = lambda: pg.evaluate("getComputedStyle(document.getElementById('lens')).display")
    tr = lambda: pg.evaluate("document.getElementById('out').style.transform")
    assert disp() == "none"
    pg.mouse.move(600, 400, steps=3); pg.wait_for_timeout(100)
    assert disp() == "block", "lens should show on hover"
    # lens must contain real artwork pixels (many distinct colours), not a blank fill
    n = pg.evaluate("(()=>{const c=document.getElementById('lens').getContext('2d').getImageData(0,0,220,220).data;const s=new Set();for(let i=0;i<c.length;i+=40)s.add(c[i]+','+c[i+1]+','+c[i+2]);return s.size})()")
    print("distinct colours in lens:", n); assert n > 50
    pg.screenshot(path="mosaic/sample_magnifier.png")
    t0 = tr(); pg.mouse.wheel(0, -600); pg.wait_for_timeout(150); assert tr() != t0, "wheel zoom"
    pg.mouse.down(); pg.mouse.move(700, 450, steps=4)
    assert disp() == "none", "lens hidden while dragging"
    pg.mouse.up()
    pg.mouse.move(600, 100); pg.mouse.move(600, 1000, steps=2)  # leave the viewport
    pg.wait_for_timeout(100); assert disp() == "none", "lens hidden after leaving"
    pg.fill("#mag", "0"); pg.dispatch_event("#mag", "input"); pg.mouse.move(600, 400, steps=2)
    assert disp() == "none", "slider 0 = off"
    print("errors:", errs, "| ALL OK"); assert not errs
    b.close()
os.remove(test)
