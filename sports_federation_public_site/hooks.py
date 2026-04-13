def post_init_hook(env):
    env["website.menu"]._cleanup_stale_public_site_menus()