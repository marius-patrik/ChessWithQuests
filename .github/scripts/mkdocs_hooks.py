import os
import shutil


def on_post_build(config):
    site_dir = config["site_dir"]
    index_html = os.path.join(site_dir, "index.html")
    if not os.path.exists(index_html):
        for candidate in ["__init__/index.html", "INDEX/index.html"]:
            src = os.path.join(site_dir, candidate)
            if os.path.exists(src):
                shutil.copyfile(src, index_html)
                print(f"Generated site/index.html from {candidate}")
                break
