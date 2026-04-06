# Install log: `sports_federation_venues`
**Status**: FAILURE  
**State before**: uninstalled  
**State after**: uninstalled  

## Error
```
XML-RPC fault: Traceback (most recent call last):
  File "/usr/lib/python3/dist-packages/odoo/addons/rpc/controllers/xmlrpc.py", line 162, in xmlrpc_2
    response = self._xmlrpc(service)
               ^^^^^^^^^^^^^^^^^^^^^
  File "/usr/lib/python3/dist-packages/odoo/addons/rpc/controllers/xmlrpc.py", line 134, in _xmlrpc
    result = dispatch_rpc(service, method, params)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/lib/python3/dist-packages/odoo/http.py", line 446, in dispatch_rpc
    return dispatch(method, params)
           ^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/lib/python3/dist-packages/odoo/service/model.py", line 133, in dispatch
    res = execute_cr(cr, uid, model, method_, args, kw)
          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/lib/python3/dist-packages/odoo/service/model.py", line 150, in execute_cr
    result = retrying(partial(call_kw, recs, method, args, kw), env)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/lib/python3/dist-packages/odoo/service/model.py", line 188, in retrying
    result = func()
             ^^^^^^
  File "/usr/lib/python3/dist-packages/odoo/service/model.py", line 97, in call_kw
    result = method(recs, *args, **kwargs)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/lib/python3/dist-packages/odoo/addons/base/models/ir_module.py", line 72, in check_and_log
    return method(self, *args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/lib/python3/dist-packages/odoo/addons/base/models/ir_module.py", line 492, in button_immediate_install
    return self._button_immediate_function(self.env.registry[self._name].button_install)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/lib/python3/dist-packages/odoo/addons/base/models/ir_module.py", line 633, in _button_immediate_function
    registry = modules.registry.Registry.new(self.env.cr.dbname, update_module=True)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/lib/python3/dist-packages/odoo/tools/func.py", line 88, in locked
    return func(inst, *args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/lib/python3/dist-packages/odoo/orm/registry.py", line 199, in new
    load_modules(
  File "/usr/lib/python3/dist-packages/odoo/modules/loading.py", line 464, in load_modules
    load_module_graph(
  File "/usr/lib/python3/dist-packages/odoo/modules/loading.py", line 217, in load_module_graph
    load_data(env, idref, 'init', kind='data', package=package)
  File "/usr/lib/python3/dist-packages/odoo/modules/loading.py", line 59, in load_data
    convert_file(env, package.name, filename, idref, mode, noupdate=kind == 'demo')
  File "/usr/lib/python3/dist-packages/odoo/tools/convert.py", line 693, in convert_file
    convert_xml_import(env, module, fp, idref, mode, noupdate)
  File "/usr/lib/python3/dist-packages/odoo/tools/convert.py", line 792, in convert_xml_import
    obj.parse(doc.getroot())
  File "/usr/lib/python3/dist-packages/odoo/tools/convert.py", line 663, in parse
    self._tag_root(de)
  File "/usr/lib/python3/dist-packages/odoo/tools/convert.py", line 616, in _tag_root
    raise ParseError(msg) from None  # Restart with "--log-handler odoo.tools.convert:DEBUG" for complete traceback
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
odoo.tools.convert.ParseError: while parsing /mnt/extra-addons/sports_federation_venues/views/match_views_inherit.xml:28
Error while parsing or validating view:

Element '<xpath expr="//group[@expand=&#39;0&#39;]">' cannot be located in parent view

View error context:
{'file': '/mnt/extra-addons/sports_federation_venues/views/match_views_inherit.xml',
 'line': 1,
 'name': 'federation.match.search.inherit.venue',
 'view': ir.ui.view(1945,),
 'view.model': 'federation.match',
 'view.parent': ir.ui.view(1821,),
 'xmlid': 'view_federation_match_search_inherit_venue'}


```

## Docker / Odoo server logs
```
<failed to collect docker logs: [Errno 2] No such file or directory: 'docker'>
```
