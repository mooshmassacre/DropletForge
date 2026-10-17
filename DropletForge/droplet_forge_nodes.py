# SPDX-License-Identifier: GPL-2.0-or-later
"""Native Scene Nodes construction for Cinema 4D 2026.

The saved scene graph itself evaluates without this Python module.
"""
import c4d
import maxon
import copy
import json
import runpy
from pathlib import Path
from functools import wraps

OP_IN = 'net.maxon.neutron.op.input'
OP_OUT = 'net.maxon.neutron.op.output'
CHILDREN = 'net.maxon.neutron.op.objectbase.children'
DATA_NAME = 'DropletForge - graph data'
LEGACY_DATA_NAMES = ('Droplet Forge - graph data', 'Droplet Generator - graph data')
DEFAULTS = {'seed': 42, 'scale': 1.0, 'density': 1.0, 'limit': 100000,
            'layers': [
                {'name': 'Big', 'count': 70, 'radius': 3.0, 'variation': 0.35, 'squish': 0.5, 'offset': 0.0, 'detail': 20},
                {'name': 'Medium', 'count': 400, 'radius': 1.35, 'variation': 0.45, 'squish': 0.5, 'offset': 0.0, 'detail': 12},
                {'name': 'Small', 'count': 1600, 'radius': 0.5, 'variation': 0.5, 'squish': 0.5, 'offset': 0.0, 'detail': 8},
                {'name': 'Micro', 'count': 3200, 'radius': 0.25, 'variation': 0.5, 'squish': 0.5, 'offset': 0.0, 'detail': 6}]}


def undoable(function):
    @wraps(function)
    def execute(document, *args, **kwargs):
        document.StartUndo()
        try:
            return function(document, *args, **kwargs)
        finally:
            document.EndUndo()
    return execute


def transaction_data(mode=maxon.nodes.UNDO_MODE.ADD):
    result = maxon.DataDictionary()
    result.Set(maxon.nodes.UndoMode, mode)
    return result


def node(graph, asset, name):
    result = graph.AddChild(maxon.Id(), maxon.Id(asset))
    result.SetValue(maxon.NODE.BASE.NAME, name)
    return result


def port(n, direction, path):
    result = n.GetInputs() if direction == 'in' else n.GetOutputs()
    for part in path.split('/'):
        result = result.FindChild(part)
        if result.IsNullValue():
            raise RuntimeError('Missing port {}:{}:{}'.format(n.GetId(), direction, path))
    return result


def set_value(n, path, value):
    # Passing DataType through SetPortValue triggers double conversion in 2026.4.
    return port(n, 'in', path).SetValue(maxon.DESCRIPTION.DATA.BASE.DEFAULTVALUE, value)


def wire(a, output, b, input):
    source, target = port(a, 'out', output), port(b, 'in', input)
    source.Connect(target)


def root_node(graph):
    for n in graph.GetRoot().GetChildren():
        if n.GetKind() == maxon.NODE_KIND.NODE and str(n.GetId()) == 'net.maxon.neutron.scene.root':
            return n
    raise RuntimeError('Default Scene Root was not found.')


def add_to_scene(root, source, output):
    children = port(root, 'in', CHILDREN)
    added = children.AddPorts(len(children.GetChildren()), 1)
    if hasattr(added, '__iter__'):
        destination = list(added)[0]
    else:
        destination = children.GetChildren()[-1]
    port(source, 'out', output).Connect(destination)


def nimbus(document, controller=None):
    if controller is not None and controller.GetType() in (180420500, 180420600):
        return controller.GetNimbusRef(maxon.NodeSpaceIdentifiers.SceneNodes)
    hook = document.FindSceneHook(c4d.SCENENODES_IDS_SCENEHOOK_ID)
    return hook.GetNimbusRef(maxon.NodeSpaceIdentifiers.SceneNodes)


def validate(config):
    config = copy.deepcopy(config)
    if len(config['layers']) == 3:
        micro = copy.deepcopy(config['layers'][2])
        micro.update(name='Micro', count=0, radius=micro['radius'] * 0.5, detail=6)
        config['layers'].append(micro)
    if len(config['layers']) != 4:
        raise ValueError('Expected four droplet layers.')
    config['scale'] = max(0.001, min(1000.0, float(config['scale'])))
    config['density'] = max(0.0, min(100.0, float(config['density'])))
    config['limit'] = max(0, min(200000, int(config['limit'])))
    config['seed'] = int(config['seed']) % 2147480000
    for layer in config['layers']:
        layer['enabled'] = bool(layer.get('enabled', True))
        layer['count'] = max(0, min(200000, int(layer['count'])))
        layer['radius'] = max(0.001, min(10000.0, float(layer['radius'])))
        layer['variation'] = max(0.0, min(0.99, float(layer['variation'])))
        layer['squish'] = max(0.01, min(2.0, float(layer['squish'])))
        layer['offset'] = float(layer['offset'])
        layer['detail'] = max(6, min(64, int(layer['detail'])))
    return config


def counts(config):
    requested = [int(layer['count'] * config['density']) if layer.get('enabled', True) else 0 for layer in config['layers']]
    total = sum(requested)
    if total <= config['limit']:
        return requested
    if total == 0:
        return [0] * len(requested)
    result = [n * config['limit'] // total for n in requested]
    remainders = sorted(range(len(requested)), key=lambda i: requested[i] * config['limit'] % total, reverse=True)
    for i in remainders[:config['limit'] - sum(result)]:
        result[i] += 1
    return result


def metadata(controller):
    if controller is None:
        return None
    for did, description in controller.GetUserDataContainer():
        if description[c4d.DESC_NAME] in (DATA_NAME,) + LEGACY_DATA_NAMES:
            try:
                data = json.loads(controller[did])
                if data['binding'].get('owner') == 'hierarchy':
                    mesh = get_link(controller, 'DropletForge mesh 0')
                    if mesh is not None:
                        for key, item in mesh.GetUserDataContainer():
                            if item[c4d.DESC_NAME] == 'DropletForge layer data':
                                data = json.loads(mesh[key])
                                break
                return did, data
            except (TypeError, ValueError):
                return None
    return None


def write_metadata(controller, data):
    found = metadata(controller)
    if found:
        did = found[0]
        for candidate, description in controller.GetUserDataContainer():
            if candidate == did and description[c4d.DESC_NAME] != DATA_NAME:
                description[c4d.DESC_NAME] = DATA_NAME
                controller.SetUserDataContainer(did, description)
                break
    else:
        description = c4d.GetCustomDataTypeDefault(c4d.DTYPE_STRING)
        description[c4d.DESC_NAME] = DATA_NAME
        description[c4d.DESC_HIDE] = True
        did = controller.AddUserData(description)
    controller[did] = json.dumps(data)
    write_layer_data(controller, data)


def write_layer_data(controller, data):
    """Keep an undoable snapshot with the replaceable layer geometry."""
    mesh = get_link(controller, 'DropletForge mesh 0')
    if mesh is None:
        return
    for did, description in mesh.GetUserDataContainer():
        if description[c4d.DESC_NAME] == 'DropletForge layer data':
            mesh[did] = json.dumps(data)
            return
    description = c4d.GetCustomDataTypeDefault(c4d.DTYPE_STRING)
    description[c4d.DESC_NAME] = 'DropletForge layer data'
    description[c4d.DESC_HIDE] = True
    mesh[mesh.AddUserData(description)] = json.dumps(data)


def find_controller(document, source_path):
    def visit(first):
        current = first
        while current:
            data = metadata(current)
            if data and data[1]['binding']['source'] == source_path:
                return current
            child = visit(current.GetDown())
            if child:
                return child
            current = current.GetNext()
        return None
    return visit(document.GetFirstObject())


def graph_for(document, controller):
    return maxon.GraphDescription.GetGraph(controller if controller.GetType() in (180420500, 180420600) else document)


def source_for(document, controller):
    stored = metadata(controller)
    if stored and stored[1]['binding'].get('owner') == 'hierarchy':
        return get_link(controller, 'DropletForge surface')
    if not stored:
        return None
    graph = graph_for(document, controller)
    imported = resolve(graph, stored[1]['binding']['source'])
    uuid = port(imported, 'in', 'object').GetPortValue()
    return nimbus(document, controller).UuidToBaseList2D(uuid)


def material_for(document, controller):
    if metadata(controller) and metadata(controller)[1]['binding'].get('owner') == 'hierarchy':
        tag = next((t for t in controller.GetTags() if t.GetName() == 'DropletForge Material' and t.CheckType(c4d.Ttexture)), None)
        return tag[c4d.TEXTURETAG_MATERIAL] if tag else None
    stored = metadata(controller)
    if not stored or not stored[1]['binding'].get('material'):
        return None
    imported = resolve(graph_for(document, controller), stored[1]['binding']['material'])
    uuid = port(imported, 'in', 'material').GetPortValue()
    return nimbus(document, controller).UuidToBaseList2D(uuid)


def find_for_surface(document, source):
    """Read existing bindings without creating nodes in an unused scene."""
    def visit(first):
        current = first
        while current:
            if metadata(current):
                try:
                    if source_for(document, current) == source:
                        return current
                except (RuntimeError, ValueError):
                    pass
            child = visit(current.GetDown())
            if child:
                return child
            current = current.GetNext()
        return None
    return visit(document.GetFirstObject())


def validate_selection(document, source, selection):
    if selection is None:
        return
    if not isinstance(selection, c4d.SelectionTag) or not selection.CheckType(c4d.Tpolygonselection):
        raise ValueError('Escolha uma Selection Tag de poligonos.')
    if selection.GetDocument() != document or selection.GetObject() != source:
        raise ValueError('A Selection Tag deve pertencer ao objeto escolhido.')


def selection_expression(selection):
    if selection is None:
        return 'all'
    selected = selection.GetBaseSelect()
    if selected.GetCount() == 0:
        return 'all - all'
    limit = selected.GetLastElement() + 1
    indexes = []
    for segment in range(selected.GetSegments()):
        first, last = selected.GetRange(segment, limit)
        indexes.extend(str(index) for index in range(first, last + 1))
    return ','.join(indexes)


def selection_for(document, controller):
    stored = metadata(controller)
    if not stored or stored[1]['binding'].get('owner') != 'hierarchy':
        return None
    paths = stored[1]['binding']['layers'][0]
    if not paths.get('selection'):
        return None
    mesh = get_link(controller, 'DropletForge mesh 0')
    if mesh is None:
        return None
    graph = maxon.GraphDescription.GetGraph(mesh)
    imported = resolve(graph, paths['selection'])
    uuid = port(imported, 'in', 'object').GetPortValue()
    return mesh.GetNimbusRef(maxon.NodeSpaceIdentifiers.SceneNodes).UuidToBaseList2D(uuid)


def apply(document, source, config=None, material=None, selection=None):
    """First application builds the nodes; subsequent applications update them."""
    controller = find_for_surface(document, source)
    if controller:
        return update(document, controller, source, config or DEFAULTS, material, selection)
    return create(document, source, config, material, selection)


def resolve(graph, path):
    found = graph.GetNode(maxon.NodePath(path))
    if found.IsNullValue() or not found.IsValid():
        raise RuntimeError('A generator node was removed. Create a new generator.')
    return found


def configure(graph, document, source, binding, config, material=None, controller=None):
    config = validate(config)
    source_node = resolve(graph, binding['source'])
    set_value(source_node, 'object', nimbus(document, controller).BaseList2DToUuid(source))
    set_value(source_node, 'timedependent', True)
    if binding.get('material'):
        material_node = resolve(graph, binding['material'])
        set_value(material_node, 'material', nimbus(document, controller).BaseList2DToUuid(material) if material else maxon.Uuid())
    limits = counts(config)
    for i, (layer, paths) in enumerate(zip(config['layers'], binding['layers'])):
        distribution = resolve(graph, paths['distribution'])
        shape = resolve(graph, paths['shape'])
        sphere = resolve(graph, paths['sphere'])
        if paths.get('material_op'):
            set_value(resolve(graph, paths['material_op']), 'net.maxon.node.bypassable.bypass', material is None)
        radius = layer['radius'] * config['scale']
        set_value(distribution, 'countin', limits[i])
        set_value(distribution, 'seedin', (config['seed'] + i * 7919) % 2147480000)
        set_value(distribution, 'minsizein', radius * (1.0 - layer['variation']))
        set_value(distribution, 'maxsizein', radius)
        set_value(distribution, 'enablescalein', True)
        set_value(distribution, 'normaloffsetin', layer['offset'])
        set_value(distribution, 'mindistancein', 0.0)
        set_value(sphere, 'net.maxon.command.modeling.primitive.sphere.radius', 1.0)
        set_value(sphere, 'net.maxon.command.modeling.primitive.sphere.segment', layer['detail'])
        set_value(shape, 'transformin/*access*scalein', maxon.Vector(1, layer['squish'], 1))
    return config


def get_link(controller, name):
    if name.startswith('DropletForge mesh '):
        index = int(name.rsplit(' ', 1)[1])
        meshes = []
        current = controller.GetDown()
        while current:
            if current.GetType() == 180420600:
                for did, description in current.GetUserDataContainer():
                    if description[c4d.DESC_NAME] == 'DropletForge layer index' and current[did] == index:
                        return current
                meshes.append(current)
            current = current.GetNext()
        return meshes[index] if index < len(meshes) else None
    for did, description in controller.GetUserDataContainer():
        if description[c4d.DESC_NAME] == name:
            return controller[did]
    return None


def set_link(controller, name, value):
    for did, description in controller.GetUserDataContainer():
        if description[c4d.DESC_NAME] == name:
            controller[did] = value
            return
    description = c4d.GetCustomDataTypeDefault(c4d.DTYPE_BASELISTLINK)
    description[c4d.DESC_NAME] = name
    description[c4d.DESC_HIDE] = True
    controller[controller.AddUserData(description)] = value


def configure_hierarchy(document, controller, binding, config, material, undo=False, source=None, meshes=None, selection=None):
    config = validate(config)
    source = source if source is not None else get_link(controller, 'DropletForge surface')
    if source is None or source.GetDocument() != document:
        raise ValueError('The linked surface is missing from this document.')
    validate_selection(document, source, selection)
    limits = counts(config)
    for i, (layer, paths) in enumerate(zip(config['layers'], binding['layers'])):
        mesh = meshes[i] if meshes is not None else get_link(controller, 'DropletForge mesh {}'.format(i))
        if mesh is None or mesh.GetDocument() != document or mesh.GetUp() != controller:
            raise ValueError('A droplet layer was removed. Undo the removal or create a new generator.')
        graph = maxon.GraphDescription.GetGraph(mesh)
        ref = mesh.GetNimbusRef(maxon.NodeSpaceIdentifiers.SceneNodes)
        with graph.BeginTransaction() as transaction:
            set_value(resolve(graph, paths['source']), 'object', ref.BaseList2DToUuid(source))
            set_value(resolve(graph, paths['source']), 'timedependent', True)
            distribution = resolve(graph, paths['distribution'])
            if not paths.get('selection'):
                selection_node = node(graph, 'net.maxon.nbo.node.legacypointpolyselectiontagimport', 'DF | Polygon selection')
                for context in ('nimbus', 'frame'):
                    graph.GetRoot().GetInputs().FindChild(context).Connect(port(selection_node, 'in', context))
                paths['selection'] = str(selection_node.GetPath())
            if not paths.get('selection_mask'):
                mask = node(graph, 'net.maxon.neutron.modeling.split', 'DF | Selected polygon surface')
                upstream = list(port(distribution, 'in', 'geometryin').GetConnections(maxon.PORT_DIR.INPUT))[0][0]
                paths['surface_geometry'] = str(upstream.GetAncestor(maxon.NODE_KIND.NODE).GetPath())
                upstream.Connect(port(mask, 'in', 'geometryin'))
                set_value(mask, 'mode', maxon.Id('polygons'))
                paths['selection_mask'] = str(mask.GetPath())
            mask = resolve(graph, paths['selection_mask'])
            set_value(mask, 'selectionstring', selection_expression(selection))
            target = port(distribution, 'in', 'geometryin')
            for connection in list(target.GetConnections(maxon.PORT_DIR.INPUT)):
                maxon.GraphModelHelper.RemoveConnection(connection[0], target)
            geometry = mask if selection is not None else resolve(graph, paths['surface_geometry'])
            wire(geometry, 'geometryout', distribution, 'geometryin')
            set_value(resolve(graph, paths['selection']), 'object', ref.BaseList2DToUuid(selection) if selection is not None else maxon.Uuid())
            set_value(distribution, 'selectionenablein', False)
            radius = layer['radius'] * config['scale']
            for key, value in [('countin', limits[i]), ('seedin', (config['seed'] + i * 7919) % 2147480000),
                               ('minsizein', radius * (1.0 - layer['variation'])), ('maxsizein', radius),
                               ('enablescalein', True), ('normaloffsetin', layer['offset']), ('mindistancein', 0.0)]:
                set_value(distribution, key, value)
            set_value(resolve(graph, paths['sphere']), 'net.maxon.command.modeling.primitive.sphere.radius', 1.0)
            set_value(resolve(graph, paths['sphere']), 'net.maxon.command.modeling.primitive.sphere.segment', layer['detail'])
            set_value(resolve(graph, paths['shape']), 'transformin/*access*scalein', maxon.Vector(1, layer['squish'], 1))
            transaction.Commit(transaction_data(maxon.nodes.UNDO_MODE.NONE))
        mesh.SetDirty(c4d.DIRTYFLAGS_DATA)
    set_link(controller, 'DropletForge surface', source)
    set_link(controller, 'DropletForge material', material)
    set_material_tag(controller, material, undo=undo)
    return config


def build_layer(controller, layer, i):
    mesh = c4d.BaseObject(180420600)
    mesh.SetName('DropletForge | ' + layer['name'])
    description = c4d.GetCustomDataTypeDefault(c4d.DTYPE_LONG)
    description[c4d.DESC_NAME] = 'DropletForge layer index'
    description[c4d.DESC_HIDE] = True
    mesh[mesh.AddUserData(description)] = i
    mesh.InsertUnderLast(controller)
    set_link(controller, 'DropletForge mesh {}'.format(i), mesh)
    graph = maxon.GraphDescription.GetGraph(mesh, createEmpty=False)
    with graph.BeginTransaction() as transaction:
        prefix = 'DF | ' + layer['name']
        imported = node(graph, 'net.maxon.nbo.node.legacyobjectimport', 'DF | Surface object')
        world = node(graph, 'net.maxon.neutron.geometry.transform_element', 'DF | Surface world coordinates')
        wire(imported, 'geometry', world, 'geometryin')
        wire(imported, 'matrix', world, 'transformin')
        distribution = node(graph, 'net.maxon.neutron.node.distribution.geometry.surfacescaledbluenoise', prefix + ' | Surface distribution')
        wire(world, 'geometryout', distribution, 'geometryin')
        iterator = node(graph, 'net.maxon.node.containeriteration', prefix + ' | Iterate')
        set_value(iterator, 'datatype', port(distribution, 'out', 'distdataout').GetValue('type'))
        wire(distribution, 'distdataout', iterator, 'in')
        sphere = node(graph, 'net.maxon.neutron.node.primitive.sphere', prefix + ' | Shape')
        shape = node(graph, 'net.maxon.neutron.geometry.transform_element', prefix + ' | Squish')
        wire(sphere, 'geometryout', shape, 'geometryin')
        placement = node(graph, 'net.maxon.neutron.geometry.transform_element', prefix + ' | Place droplets')
        wire(shape, 'geometryout', placement, 'geometryin')
        wire(iterator, 'out/matrix', placement, 'transformin')
        merged = node(graph, 'net.maxon.neutron.geometry.connect_geometries', prefix + ' | Droplet mesh')
        wire(placement, 'geometryout', merged, 'geometryin/_0')
        port(merged, 'out', 'geometryout').Connect(graph.GetRoot().GetOutputs().FindChild('geometryout'))
        paths = {'source': str(imported.GetPath()), 'distribution': str(distribution.GetPath()),
                 'sphere': str(sphere.GetPath()), 'shape': str(shape.GetPath())}
        transaction.Commit(transaction_data(maxon.nodes.UNDO_MODE.NONE))
    mesh.MakeTag(c4d.Tphong)
    return mesh, paths


@undoable
def create(document, source, config=None, material=None, selection=None):
    if source is None or source.GetDocument() != document:
        raise ValueError('Select a polygon object or a parametric mesh in this document.')
    if metadata(source):
        raise ValueError('Choose the surface object instead of the generator controller.')
    validate_selection(document, source, selection)
    config = validate(config or DEFAULTS)
    controller = c4d.BaseObject(c4d.Onull)
    controller.SetName('DropletForge | ' + source.GetName())
    document.InsertObject(controller)
    binding = {'version': 6, 'owner': 'hierarchy', 'layers': []}
    try:
        set_link(controller, 'DropletForge surface', source)
        for i, layer in enumerate(config['layers']):
            mesh, paths = build_layer(controller, layer, i)
            binding['layers'].append(paths)
        binding['source'] = binding['layers'][0]['source']
        config = configure_hierarchy(document, controller, binding, config, material, selection=selection)
        write_metadata(controller, {'binding': binding, 'config': config})
        brand_controller(controller)
    except BaseException:
        controller.Remove()
        raise
    document.AddUndo(c4d.UNDOTYPE_NEWOBJ, controller)
    document.SetActiveObject(controller)
    c4d.EventAdd()
    return controller


@undoable
def update(document, controller, source, config, material=None, selection=None, _record_undo=True):
    stored = metadata(controller)
    if not stored or controller.GetDocument() != document:
        raise ValueError('Select the DropletForge controller to edit it.')
    if stored[1]['binding'].get('owner') != 'hierarchy':
        return migrate(document, controller, source, config, material, selection)
    config = validate(config)
    validate_selection(document, source, selection)
    if source is None or source.GetDocument() != document:
        raise ValueError('Choose a surface in this document.')
    layers = [get_link(controller, 'DropletForge mesh {}'.format(i)) for i in range(len(stored[1]['binding']['layers']))]
    if any(mesh is None or mesh.GetUp() != controller for mesh in layers):
        raise ValueError('A droplet layer was removed. Undo the removal or delete the group and apply again.')
    if len(layers) < len(config['layers']) and _record_undo:
        replacement = controller.GetClone()
        replacement.InsertAfter(controller)
        try:
            update.__wrapped__(document, replacement, source, config, material, selection, _record_undo=False)
        except BaseException:
            replacement.Remove()
            raise
        document.AddUndo(c4d.UNDOTYPE_DELETEOBJ, controller)
        controller.Remove()
        document.AddUndo(c4d.UNDOTYPE_NEWOBJ, replacement)
        document.SetActiveObject(replacement)
        return replacement
    if _record_undo:
        document.AddUndo(c4d.UNDOTYPE_CHANGE_SMALL, controller)
    write_layer_data(controller, stored[1])
    replacements = []
    try:
        for i, mesh in enumerate(layers):
            replacement = mesh.GetClone()
            replacement.InsertAfter(mesh)
            replacements.append(replacement)
            set_link(controller, 'DropletForge mesh {}'.format(i), replacement)
        for i in range(len(layers), len(config['layers'])):
            replacement, paths = build_layer(controller, config['layers'][i], i)
            replacements.append(replacement)
            stored[1]['binding']['layers'].append(paths)
        config = configure_hierarchy(document, controller, stored[1]['binding'], config, material, undo=_record_undo, source=source, meshes=replacements, selection=selection)
    except BaseException:
        for replacement in replacements:
            replacement.Remove()
        for i, mesh in enumerate(layers):
            set_link(controller, 'DropletForge mesh {}'.format(i), mesh)
        raise
    for old, new in zip(layers, replacements):
        if _record_undo:
            document.AddUndo(c4d.UNDOTYPE_DELETEOBJ, old)
        old.Remove()
        if _record_undo:
            document.AddUndo(c4d.UNDOTYPE_NEWOBJ, new)
    controller.SetName('DropletForge | ' + source.GetName())
    brand_controller(controller, undo=_record_undo)
    stored[1]['binding']['version'] = 6
    write_metadata(controller, {'binding': stored[1]['binding'], 'config': config})
    c4d.EventAdd()
    return controller


def saved_render_engine():
    preferences = runpy.run_path(str(Path(__file__).with_name('forge_preferences.py')))
    saved = preferences['load_preferences']()
    return saved['engine'] if saved['language'] is not None else 'Standard'


def brand_controller(controller, undo=False):
    folder = Path(__file__).resolve().parent
    icon = folder / 'res' / 'droplet_simple.png'
    if not icon.exists():
        icon = folder / 'plugin' / 'DropletForge' / 'res' / 'droplet_simple.png'
    if icon.exists():
        controller[c4d.ID_BASELIST_ICON_FILE] = str(icon)
        controller[c4d.ID_BASELIST_ICON_COLORIZE_MODE] = c4d.ID_BASELIST_ICON_COLORIZE_MODE_NONE
    if saved_render_engine() != 'Octane':
        for tag in controller.GetTags():
            if tag.CheckType(1029603) and tag.GetName() == 'DropletForge':
                if undo:
                    controller.GetDocument().AddUndo(c4d.UNDOTYPE_DELETEOBJ, tag)
                tag.Remove()
        return
    if c4d.plugins.FindPlugin(1029603, c4d.PLUGINTYPE_TAG) is not None:
        tag = next((tag for tag in controller.GetTags() if tag.CheckType(1029603) and tag.GetName() == 'DropletForge'), None)
        if tag is None and controller.GetTag(1029603) is not None:
            return
        if tag is None:
            tag = controller.MakeTag(1029603)
            if undo:
                controller.GetDocument().AddUndo(c4d.UNDOTYPE_NEWOBJ, tag)
        elif undo and tag.GetName() != 'DropletForge':
            controller.GetDocument().AddUndo(c4d.UNDOTYPE_CHANGE, tag)
        tag.SetName('DropletForge')


@undoable
def sync_engine_tags(document):
    def visit(first):
        current = first
        while current:
            if metadata(current):
                brand_controller(current, undo=True)
            visit(current.GetDown())
            current = current.GetNext()
    visit(document.GetFirstObject())
    c4d.EventAdd()


def set_material_tag(controller, material, undo=False):
    document = controller.GetDocument()
    tag = next((t for t in controller.GetTags() if t.GetName() == 'DropletForge Material' and t.CheckType(c4d.Ttexture)), None)
    if material is None:
        if tag:
            if undo:
                document.AddUndo(c4d.UNDOTYPE_DELETEOBJ, tag)
            tag.Remove()
        return
    if tag is None:
        tag = c4d.BaseTag(c4d.Ttexture)
        tag.SetName('DropletForge Material')
        controller.InsertTag(tag)
        if undo:
            document.AddUndo(c4d.UNDOTYPE_NEWOBJ, tag)
    elif undo:
        document.AddUndo(c4d.UNDOTYPE_CHANGE, tag)
    tag[c4d.TEXTURETAG_MATERIAL] = material
    tag[c4d.TEXTURETAG_PROJECTION] = c4d.TEXTURETAG_PROJECTION_UVW


def migrate(document, controller, source, config, material, selection=None):
    """Replace a document-graph binding with an object-owned generator."""
    graph = graph_for(document, controller)
    binding = metadata(controller)[1]['binding']
    seeds = [binding['source'], binding.get('material')]
    for layer in binding['layers']:
        seeds.extend(layer.values())
    owned = {}
    def collect(n):
        key = str(n.GetPath())
        if key in owned:
            return
        owned[key] = n
        def outputs(p):
            for connection in p.GetConnections(maxon.PORT_DIR.OUTPUT):
                other = connection[0].GetAncestor(maxon.NODE_KIND.NODE)
                if other and str(other.GetValue(maxon.NODE.BASE.NAME)).startswith('DF | '):
                    collect(other)
            for child in p.GetChildren():
                outputs(child)
        for output in n.GetOutputs().GetChildren():
            outputs(output)
    for path in seeds:
        if path:
            collect(resolve(graph, path))
    replacement = create.__wrapped__(document, source, config, material, selection)
    for tag in controller.GetTags():
        if tag.CheckType(1029603):
            existing = replacement.GetTag(1029603)
            if existing:
                existing.Remove()
        replacement.InsertTag(tag.GetClone())
    brand_controller(replacement)
    with graph.BeginTransaction() as transaction:
        for n in owned.values():
            n.Remove()
        transaction.Commit(transaction_data())
    document.AddUndo(c4d.UNDOTYPE_DELETEOBJ, controller)
    controller.Remove()
    document.SetActiveObject(replacement)
    c4d.EventAdd()
    return replacement
