# SPDX-License-Identifier: GPL-2.0-or-later
"""Cinema 4D command plugin. Graphs are created only when applying droplets."""
from pathlib import Path
import runpy
import c4d

# Local development identifier, also used in Maxon's command-plugin examples.
# Replace with a Plugin Cafe assigned identifier before public distribution.
PLUGIN_ID = 1000001
PLUGIN_NAME = 'DropletForge'
PLUGIN_VERSION = '1.0'
ROOT = Path(__file__).resolve().parent
UI = runpy.run_path(str(ROOT / 'Droplet_Forge_C4D.py'))


class DropletCommand(c4d.plugins.CommandData):
    dialog = None

    def Execute(self, document):
        preferences = UI['ensure_preferences']()
        if preferences is None:
            return False
        if self.dialog is None:
            self.dialog = UI['DropletDialog'](preferences)
        result = self.dialog.Open(c4d.DLG_TYPE_ASYNC, pluginid=PLUGIN_ID,
                                  defaultw=430, defaulth=540)
        if result:
            self.dialog.load_selection()
        return result

    def RestoreLayout(self, secret):
        preferences = UI['ensure_preferences']()
        if preferences is None:
            return False
        if self.dialog is None:
            self.dialog = UI['DropletDialog'](preferences)
        return self.dialog.Restore(pluginid=PLUGIN_ID, secret=secret)

    def GetState(self, document):
        return c4d.CMD_ENABLED

    def GetScriptName(self):
        return 'droplet_forge.open_window'


def register():
    existing = c4d.plugins.FindPlugin(PLUGIN_ID, c4d.PLUGINTYPE_ANY)
    if existing is not None:
        raise RuntimeError('DropletForge: plugin ID {} already belongs to {}. '
                           'Assign a unique Plugin Cafe ID before installing.'.format(PLUGIN_ID,existing.GetName()))
    icon = c4d.bitmaps.BaseBitmap()
    result = icon.InitWith(str(ROOT / 'res' / 'icon.png'))
    if result[0] != c4d.IMAGERESULT_OK:
        raise RuntimeError('DropletForge icon could not be loaded.')
    return c4d.plugins.RegisterCommandPlugin(
        id=PLUGIN_ID, str=PLUGIN_NAME, info=0, icon=icon,
        help='Open DropletForge. Scene Nodes are created when applying droplets to an object.',
        dat=DropletCommand())


if __name__ == '__main__':
    if not register():
        raise RuntimeError('DropletForge could not be registered.')
