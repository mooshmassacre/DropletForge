# SPDX-License-Identifier: GPL-2.0-or-later
"""Persistent user preferences and language selection for DropletForge."""
from pathlib import Path
import json
import os
import c4d

DEFAULTS = {'language': None, 'engine': 'Octane'}
TEXT = {
 'PT/BR': {'object':'Objeto','general':'Geral','seed':'Semente','scale':'Escala geral','density':'Quantidade x','limit':'Limite total','big':'Grandes','medium':'Médias','small':'Pequenas','micro':'Micro','active':'Ativo','count':'Quantidade','size':'Tamanho (cm)','variation':'Variação do tamanho','squish':'Achatamento','offset':'Deslocamento (cm)','detail':'Detalhe','apply':'Criar / Atualizar','selected':'Usar objeto selecionado','language':'Idioma','engine':'Render Engine','save':'Salvar','cancel':'Cancelar','choose':'Escolha o idioma / Choose your language','no_object':'Escolha um objeto no campo Objeto.','not_material':'O campo Material espera um material da cena.','no_octane':'Octane não está instalado. Selecione Standard em Config.','material_error':'Não foi possível criar o material.','preferences_error':'Não foi possível salvar as preferências.','selection_type':'Escolha uma Selection Tag de polígonos.','selection_owner':'A Selection Tag deve pertencer ao objeto escolhido.'},
 'EN': {'object':'Object','general':'General','seed':'Seed','scale':'Global scale','density':'Count multiplier','limit':'Total limit','big':'Large','medium':'Medium','small':'Small','micro':'Micro','active':'Enabled','count':'Count','size':'Size (cm)','variation':'Size variation','squish':'Flattening','offset':'Offset (cm)','detail':'Detail','apply':'Create / Update','selected':'Use selected object','language':'Language','engine':'Render Engine','save':'Save','cancel':'Cancel','choose':'Choose your language / Escolha o idioma','no_object':'Choose an object in the Object field.','not_material':'The Material field requires a scene material.','no_octane':'Octane is not installed. Select Standard in Config.','material_error':'Could not create the material.','preferences_error':'Could not save preferences.','selection_type':'Choose a polygon Selection Tag.','selection_owner':'The Selection Tag must belong to the selected object.'}}

def tr(preferences, key):
    return TEXT.get(preferences.get('language'), TEXT['PT/BR'])[key]

def preference_path():
    return Path(c4d.storage.GeGetC4DPath(c4d.C4D_PATH_PREFS)) / 'DropletForge' / 'preferences.json'

def load_preferences(path=None):
    prefs = dict(DEFAULTS)
    try:
        data = json.loads(Path(path or preference_path()).read_text(encoding='utf-8'))
        if not isinstance(data, dict):return prefs
        if data.get('language') in TEXT: prefs['language'] = data['language']
        if data.get('engine') in ('Octane', 'Standard'): prefs['engine'] = data['engine']
    except (OSError, ValueError, TypeError):
        pass
    return prefs

def save_preferences(preferences, path=None):
    if preferences.get('language') not in TEXT or preferences.get('engine') not in ('Octane','Standard'):
        raise ValueError('Invalid DropletForge preferences.')
    target = Path(path or preference_path())
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix('.tmp')
    temporary.write_text(json.dumps(preferences, ensure_ascii=False, indent=2), encoding='utf-8')
    os.replace(str(temporary), str(target))

class SettingsDialog(c4d.gui.GeDialog):
    def __init__(self, preferences, first_run=False):
        self.preferences = dict(preferences)
        self.first_run = first_run
        self.accepted = False

    def CreateLayout(self):
        self.SetTitle('DropletForge | '+('Language / Idioma' if self.first_run else 'Config'))
        self.GroupBorderSpace(16,16,16,16)
        if self.first_run: self.AddStaticText(1,c4d.BFH_LEFT,name=tr(self.preferences,'choose'))
        self.GroupBegin(2,c4d.BFH_SCALEFIT,cols=2)
        self.AddStaticText(3,c4d.BFH_LEFT,name='Language / Idioma' if self.first_run else tr(self.preferences,'language'))
        self.AddComboBox(10,c4d.BFH_SCALEFIT,initw=160,inith=0)
        self.AddChild(10,0,'EN');self.AddChild(10,1,'PT/BR')
        if not self.first_run:
            self.AddStaticText(4,c4d.BFH_LEFT,name=tr(self.preferences,'engine'))
            self.AddComboBox(11,c4d.BFH_SCALEFIT,initw=160,inith=0)
            self.AddChild(11,0,'Octane');self.AddChild(11,1,'Standard')
        self.GroupEnd()
        self.GroupBegin(20,c4d.BFH_SCALEFIT,cols=2)
        self.GroupBorderSpace(0,12,0,0)
        self.AddButton(21,c4d.BFH_SCALEFIT,name='OK' if self.first_run else tr(self.preferences,'save'))
        self.AddButton(22,c4d.BFH_SCALEFIT,name='Cancel / Cancelar' if self.first_run else tr(self.preferences,'cancel'))
        self.GroupEnd()
        return True

    def InitValues(self):
        self.SetInt32(10,0 if self.preferences.get('language')=='EN' else 1)
        if not self.first_run:self.SetInt32(11,0 if self.preferences['engine']=='Octane' else 1)
        return True

    def Command(self,id,message):
        if id==22:self.Close()
        elif id==21:
            prefs={'language':'EN' if self.GetInt32(10)==0 else 'PT/BR', 'engine':self.preferences['engine'] if self.first_run else ('Octane' if self.GetInt32(11)==0 else 'Standard')}
            try:save_preferences(prefs)
            except OSError as error:
                c4d.gui.MessageDialog(tr(prefs,'preferences_error')+'\n'+str(error));return False
            self.preferences=prefs;self.accepted=True;self.Close()
        return True

def ensure_preferences():
    prefs=load_preferences()
    if prefs['language'] is None:
        dialog=SettingsDialog(prefs,first_run=True)
        dialog.Open(c4d.DLG_TYPE_MODAL,defaultw=350)
        return dialog.preferences if dialog.accepted else None
    return prefs
