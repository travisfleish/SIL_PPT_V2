# matplotlib_font_fix.py
"""
Import this at the beginning of your scripts to ensure Red Hat Display is available
"""
import matplotlib.font_manager as fm
import os

def setup_red_hat_display():
    """Add Red Hat Display fonts to matplotlib"""
    font_dir = os.path.expanduser('~/Library/Fonts')
    font_added = False

    if os.path.exists(font_dir):
        for font_file in os.listdir(font_dir):
            if 'RedHatDisplay' in font_file and font_file.endswith('.ttf'):
                try:
                    font_path = os.path.join(font_dir, font_file)
                    fm.fontManager.addfont(font_path)
                    font_added = True
                except:
                    pass

    if font_added:
        print("Red Hat Display fonts loaded into matplotlib")

    return font_added

# Auto-run on import
setup_red_hat_display()
