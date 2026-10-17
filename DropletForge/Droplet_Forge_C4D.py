# SPDX-License-Identifier: GPL-2.0-or-later
"""Open this file in Cinema 4D 2026's Script Manager and execute it."""
from pathlib import Path
import copy
import runpy
import traceback
import c4d

API = runpy.run_path(str(Path(__file__).with_name('droplet_forge_nodes.py')))
PREFS = runpy.run_path(str(Path(__file__).with_name('forge_preferences.py')))
ensure_preferences = PREFS['ensure_preferences']


def create_water_drop(document, engine='Octane', language='PT/BR', controller=None):
    preferences = {'language': language, 'engine': engine}
    if engine == 'Octane':
        material_type = 1029501
        if c4d.plugins.FindPlugin(material_type, c4d.PLUGINTYPE_MATERIAL) is None:
            raise RuntimeError(PREFS['tr'](preferences, 'no_octane'))
        material = c4d.BaseMaterial(material_type)
        if material is None:
            raise RuntimeError(PREFS['tr'](preferences, 'material_error'))
        material[c4d.OCT_MATERIAL_TYPE] = c4d.OCT_MAT_TYPE_SPECULAR
        material[c4d.OCT_MATERIAL_INDEX] = 1.333
        material[c4d.OCT_MATERIAL_ROUGHNESS_FLOAT] = 0.0
        material[c4d.OCT_MATERIAL_SPECULAR_COLOR] = c4d.Vector(1.0)
        material[c4d.OCT_MATERIAL_SPECULAR_FLOAT] = 1.0
        material[c4d.OCT_MATERIAL_TRANSMISSION_COLOR] = c4d.Vector(1.0)
        material[c4d.OCT_MATERIAL_TRANSMISSION_FLOAT] = 1.0
    elif engine == 'Standard':
        material = c4d.BaseMaterial(c4d.Mmaterial)
        material[c4d.MATERIAL_USE_COLOR] = False
        material[c4d.MATERIAL_USE_TRANSPARENCY] = True
        material[c4d.MATERIAL_TRANSPARENCY_COLOR] = c4d.Vector(1.0)
        material[c4d.MATERIAL_TRANSPARENCY_BRIGHTNESS] = 1.0
        material[c4d.MATERIAL_TRANSPARENCY_REFRACTION] = 1.333
        material[c4d.MATERIAL_USE_REFLECTION] = True
    else:
        raise ValueError('Unknown render engine: '+str(engine))
    material.SetName('Water Drop')
    material.Message(c4d.MSG_UPDATE)
    document.StartUndo()
    try:
        document.InsertMaterial(material)
        document.AddUndo(c4d.UNDOTYPE_NEWOBJ, material)
        if controller is not None:
            API['set_material_tag'](controller, material, undo=True)
            API['brand_controller'](controller, undo=True)
    finally:
        document.EndUndo()
    c4d.EventAdd()
    return material


class DropletDialog(c4d.gui.GeDialog):
    def __init__(self, preferences=None):
        self.preferences = dict(preferences or PREFS['load_preferences']())
        self.controller = None
        self.binding_source = None
        self.config = API['validate'](API['DEFAULTS'])
        self.link = None
        self.material_link = None
        self.selection_link = None

    def text(self, key):
        return PREFS['tr'](self.preferences, key)

    def CreateLayout(self):
        self.GroupBegin(900, c4d.BFH_SCALEFIT, cols=1)
        self.build_layout()
        self.GroupEnd()
        return True

    def build_layout(self):
        self.SetTitle('DropletForge 1.0 | Scene Nodes')
        self.GroupBorderSpace(12, 12, 12, 12)
        self.AddStaticText(10, c4d.BFH_LEFT, name=self.text('object'))
        self.link = self.AddCustomGui(100, c4d.CUSTOMGUI_LINKBOX, '', c4d.BFH_SCALEFIT, 350, 0)
        self.AddStaticText(12, c4d.BFH_LEFT, name='Selection Tag')
        self.selection_link = self.AddCustomGui(103, c4d.CUSTOMGUI_LINKBOX, '', c4d.BFH_SCALEFIT, 350, 0)
        self.AddStaticText(11, c4d.BFH_LEFT, name='Material')
        self.GroupBegin(104, c4d.BFH_SCALEFIT, cols=2)
        self.material_link = self.AddCustomGui(102, c4d.CUSTOMGUI_LINKBOX, '', c4d.BFH_SCALEFIT, 240, 0)
        self.AddButton(105, c4d.BFH_RIGHT, initw=105, name='+ Drop Oct Tx' if self.preferences['engine']=='Octane' else '+ Drop Std Tx')
        self.GroupEnd()
        self.GroupBegin(200, c4d.BFH_SCALEFIT, cols=2, title=self.text('general'))
        self.GroupBorder(c4d.BORDER_GROUP_IN)
        self.GroupBorderSpace(10, 10, 10, 10)
        for id, label in [(201, self.text('seed')), (202, self.text('scale')), (203, self.text('density')), (204, self.text('limit'))]:
            self.AddStaticText(id+10000, c4d.BFH_LEFT, name=label)
            self.AddEditNumberArrows(id, c4d.BFH_SCALEFIT)
        self.GroupEnd()
        self.TabGroupBegin(300, c4d.BFH_SCALEFIT)
        for i, name in enumerate([self.text(key) for key in ('big', 'medium', 'small', 'micro')]):
            base = 1000 + i * 100
            self.GroupBegin(base, c4d.BFH_SCALEFIT, cols=2, title=name)
            self.GroupBorderSpace(10, 10, 10, 10)
            self.AddCheckbox(base+7, c4d.BFH_LEFT, 0, 0, name=self.text('active'))
            self.AddStaticText(base+10020, c4d.BFH_LEFT, name='')
            for j, label in enumerate([self.text(key) for key in ('count','size','variation','squish','offset','detail')]):
                self.AddStaticText(base+j+10000, c4d.BFH_LEFT, name=label)
                self.AddEditNumberArrows(base+j+1, c4d.BFH_SCALEFIT)
            self.GroupEnd()
        self.GroupEnd()
        self.GroupBegin(399, c4d.BFH_SCALEFIT, cols=1)
        self.GroupBorderSpace(0, 10, 0, 0)
        self.GroupBegin(400, c4d.BFH_SCALEFIT, cols=4)
        self.AddButton(401, c4d.BFH_SCALEFIT, name=self.text('apply'))
        self.AddButton(101, c4d.BFH_SCALEFIT, name=self.text('selected'))
        self.AddButton(402, c4d.BFH_SCALEFIT, name='Demo Scene')
        self.AddButton(403, c4d.BFH_SCALEFIT, name='Config')
        self.GroupEnd()
        self.GroupEnd()
        return True

    def fill(self):
        config = self.config
        self.SetInt32(201, config['seed'], min=0, max=2147480000)
        self.SetFloat(202, config['scale'], min=0.001, max=1000.0, step=0.1)
        self.SetFloat(203, config['density'], min=0.0, max=100.0, step=0.1)
        self.SetInt32(204, config['limit'], min=0, max=200000)
        for i, layer in enumerate(config['layers']):
            base = 1000 + i * 100
            self.SetBool(base+7, layer.get('enabled', True))
            for j in range(1, 7):
                self.Enable(base+j, layer.get('enabled', True))
                self.Enable(base+j-1+10000, layer.get('enabled', True))
            self.SetInt32(base+1, layer['count'], min=0, max=200000)
            self.SetFloat(base+2, layer['radius'], min=0.001, max=10000.0, step=0.1)
            self.SetFloat(base+3, layer['variation'], min=0.0, max=0.99, step=0.05)
            self.SetFloat(base+4, layer['squish'], min=0.01, max=2.0, step=0.05)
            self.SetFloat(base+5, layer['offset'], min=-10000.0, max=10000.0, step=0.1)
            self.SetInt32(base+6, layer['detail'], min=6, max=64)

    def read(self):
        config = copy.deepcopy(self.config)
        config.update(seed=self.GetInt32(201), scale=self.GetFloat(202),
                      density=self.GetFloat(203), limit=self.GetInt32(204))
        for i, layer in enumerate(config['layers']):
            base = 1000 + i * 100
            layer.update(enabled=self.GetBool(base+7), count=self.GetInt32(base+1), radius=self.GetFloat(base+2),
                         variation=self.GetFloat(base+3), squish=self.GetFloat(base+4),
                         offset=self.GetFloat(base+5), detail=self.GetInt32(base+6))
        return API['validate'](config)

    def load_selection(self):
        document = c4d.documents.GetActiveDocument()
        selected = document.GetActiveObject()
        if selected is not None and selected.GetUp() is not None:
            parent = selected.GetUp()
            parent_data = API['metadata'](parent)
            if parent_data and parent_data[1]['binding'].get('owner') == 'hierarchy':
                selected = parent
        if selected is not None and API['metadata'](selected) is None:
            existing = API['find_for_surface'](document, selected)
            if existing is not None:
                selected = existing
        stored = API['metadata'](selected)
        if stored:
            self.controller = selected
            self.binding_source = stored[1]['binding']['source']
            self.config = API['validate'](stored[1]['config'])
            self.link.SetLink(API['source_for'](document, selected))
            self.material_link.SetLink(API['material_for'](document, selected))
            self.selection_link.SetLink(API['selection_for'](document, selected))
        elif selected is not None:
            self.controller = None
            self.binding_source = None
            self.link.SetLink(selected)
            self.selection_link.SetLink(None)
        else:
            self.controller = None
            self.binding_source = None
            self.link.SetLink(None)
            self.selection_link.SetLink(None)
            self.material_link.SetLink(None)
        self.fill()

    def InitValues(self):
        self.fill()
        self.load_selection()
        return True

    def Command(self, id, message):
        try:
            if id in (1007, 1107, 1207, 1307):
                self.config = self.read()
                self.fill()
                document = c4d.documents.GetActiveDocument()
                source = self.link.GetLink(document)
                existing = API['find_for_surface'](document, source) if source is not None else None
                if existing is not None:
                    self.controller = API['apply'](document, source, self.config, self.material_link.GetLink(document), self.selection_link.GetLink(document))
                    self.binding_source = API['metadata'](self.controller)[1]['binding']['source']
            elif id == 100:
                document = c4d.documents.GetActiveDocument()
                selection = self.selection_link.GetLink(document)
                if selection is not None and (not isinstance(selection, c4d.SelectionTag) or selection.GetObject() != self.link.GetLink(document)):
                    self.selection_link.SetLink(None)
            elif id == 101:
                self.load_selection()
            elif id == 105:
                document = c4d.documents.GetActiveDocument()
                source = self.link.GetLink(document)
                controller = API['find_for_surface'](document, source) if source is not None else None
                material = create_water_drop(document, self.preferences['engine'], self.preferences['language'], controller)
                self.material_link.SetLink(material)
            elif id == 403:
                self.config = self.read()
                document = c4d.documents.GetActiveDocument()
                links = (self.link.GetLink(document), self.selection_link.GetLink(document), self.material_link.GetLink(document))
                settings = PREFS['SettingsDialog'](self.preferences)
                settings.Open(c4d.DLG_TYPE_MODAL, defaultw=350)
                if settings.accepted:
                    self.preferences = settings.preferences
                    API['sync_engine_tags'](document)
                    self.LayoutFlushGroup(900)
                    self.build_layout()
                    self.LayoutChanged(900)
                    self.fill()
                    for field, value in zip((self.link, self.selection_link, self.material_link), links):
                        field.SetLink(value)
            elif id == 402:
                document = c4d.documents.BaseDocument()
                document.SetDocumentName('DropletForge - example')
                source = c4d.BaseObject(c4d.Osphere)
                source[c4d.PRIM_SPHERE_RAD] = 100.0
                source[c4d.PRIM_SPHERE_SUB] = 48
                source.SetName(self.text('object'))
                document.InsertObject(source)
                c4d.documents.InsertBaseDocument(document)
                c4d.documents.SetActiveDocument(document)
                self.controller = API['create'](document, source, self.read())
                self.binding_source = API['metadata'](self.controller)[1]['binding']['source']
                self.link.SetLink(source)
                self.selection_link.SetLink(None)
            elif id == 401:
                document = c4d.documents.GetActiveDocument()
                source = self.link.GetLink(document)
                if source is None:
                    raise ValueError(self.text('no_object'))
                self.config = self.read()
                material = self.material_link.GetLink(document)
                if material is not None and not isinstance(material,c4d.BaseMaterial):
                    raise ValueError(self.text('not_material'))
                selection = self.selection_link.GetLink(document)
                API['validate_selection'](document, source, selection)
                self.controller = API['apply'](document, source, self.config, material, selection)
                self.binding_source = API['metadata'](self.controller)[1]['binding']['source']
            return True
        except Exception as error:
            print(traceback.format_exc())
            message = str(error)
            selection_errors = {'Escolha uma Selection Tag de poligonos.':'selection_type', 'A Selection Tag deve pertencer ao objeto escolhido.':'selection_owner'}
            c4d.gui.MessageDialog(self.text(selection_errors[message]) if message in selection_errors else message)
            return False


def main():
    preferences = ensure_preferences()
    if preferences is None:
        return False
    legacy = getattr(c4d, '_droplet_generator_dialog', None)
    if legacy is not None:
        legacy.Close()
    legacy_command = getattr(c4d, '_droplet_plugin_validation_command', None)
    if legacy_command is not None and legacy_command.dialog is not None:
        legacy_command.dialog.Close()
    previous = getattr(c4d, '_droplet_forge_dialog', None)
    if previous is not None:
        previous.Close()
    c4d._droplet_forge_dialog = DropletDialog(preferences)
    c4d._droplet_forge_dialog.Open(c4d.DLG_TYPE_ASYNC, defaultw=430, defaulth=480)


if __name__ == '__main__':
    main()
