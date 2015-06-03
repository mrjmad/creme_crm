# -*- coding: utf-8 -*-

from django.conf.urls import patterns, url

from creme.opportunities import opportunity_model_is_custom

from . import act_model_is_custom, pattern_model_is_custom, strategy_model_is_custom


urlpatterns = patterns('creme.commercial.views',
    (r'^$', 'portal.portal'),

    (r'^salesmen$',     'salesman.listview'), #TODO: list_contacts + property
    (r'^salesman/add$', 'salesman.add'),

    (r'^approach/add/(?P<entity_id>\d+)/$', 'commercial_approach.add'),

    #Segments
    (r'^market_segments$',                          'market_segment.listview'),
    (r'^market_segment/add$',                       'market_segment.add'),
    (r'^market_segment/edit/(?P<segment_id>\d+)$',  'market_segment.edit'),

    #Objectives & opportunities
    (r'^act/(?P<act_id>\d+)/add/objective$',               'act.add_objective'),
    (r'^act/(?P<act_id>\d+)/add/objectives_from_pattern$', 'act.add_objectives_from_pattern'),
    (r'^objective/(?P<objective_id>\d+)/edit$',            'act.edit_objective'),
    (r'^objective/(?P<objective_id>\d+)/incr$',            'act.incr_objective_counter'),
    (r'^objective/(?P<objective_id>\d+)/create_entity$',   'act.create_objective_entity'),

    #Pattern component
    (r'^objective_pattern/(?P<objpattern_id>\d+)/add_component$',      'act.add_pattern_component'),
    (r'^objective_pattern/component/(?P<component_id>\d+)/add_child',  'act.add_child_pattern_component'),
    (r'^objective_pattern/component/(?P<component_id>\d+)/add_parent', 'act.add_parent_pattern_component'),

    #Segments
    (r'^strategy/(?P<strategy_id>\d+)/add/segment/$',                      'strategy.add_segment'),
    (r'^strategy/(?P<strategy_id>\d+)/link/segment/$',                     'strategy.link_segment'),
    (r'^strategy/(?P<strategy_id>\d+)/segment/edit/(?P<seginfo_id>\d+)/$', 'strategy.edit_segment'),

    #Assets
    (r'^strategy/(?P<strategy_id>\d+)/add/asset/$', 'strategy.add_asset'),
    (r'^asset/edit/(?P<asset_id>\d+)/$',            'strategy.edit_asset'),

    #Charms
    (r'^strategy/(?P<strategy_id>\d+)/add/charm/$', 'strategy.add_charm'),
    (r'^charm/edit/(?P<charm_id>\d+)/$',            'strategy.edit_charm'),

    #Evaluated organisations
    (r'^strategy/(?P<strategy_id>\d+)/add/organisation/$',                        'strategy.add_evalorga'),
    (r'^strategy/(?P<strategy_id>\d+)/organisation/delete$',                      'strategy.delete_evalorga'),
    (r'^strategy/(?P<strategy_id>\d+)/organisation/(?P<orga_id>\d+)/evaluation$', 'strategy.orga_evaluation'),
    (r'^strategy/(?P<strategy_id>\d+)/organisation/(?P<orga_id>\d+)/synthesis$',  'strategy.orga_synthesis'),

    #Scores & category
    (r'^strategy/(?P<strategy_id>\d+)/set_asset_score$', 'strategy.set_asset_score'),
    (r'^strategy/(?P<strategy_id>\d+)/set_charm_score$', 'strategy.set_charm_score'),
    (r'^strategy/(?P<strategy_id>\d+)/set_segment_cat$', 'strategy.set_segment_category'),

    #Blocks
    (r'^blocks/assets_matrix/(?P<strategy_id>\d+)/(?P<orga_id>\d+)/$',        'strategy.reload_assets_matrix'),
    (r'^blocks/charms_matrix/(?P<strategy_id>\d+)/(?P<orga_id>\d+)/$',        'strategy.reload_charms_matrix'),
    (r'^blocks/assets_charms_matrix/(?P<strategy_id>\d+)/(?P<orga_id>\d+)/$', 'strategy.reload_assets_charms_matrix'),
)

if not act_model_is_custom():
    urlpatterns += patterns('creme.commercial.views.act',
        url(r'^acts$',                     'listview',   name='commercial__list_acts'),
        url(r'^act/add$',                  'add',        name='commercial__create_act'),
        url(r'^act/edit/(?P<act_id>\d+)$', 'edit',       name='commercial__edit_act'),
        url(r'^act/(?P<act_id>\d+)$',      'detailview', name='commercial__view_act'),
    )

if not opportunity_model_is_custom():
    urlpatterns += patterns('creme.commercial.views.act',
        url(r'^act/(?P<act_id>\d+)/add/opportunity$', 'add_opportunity', name='commercial__create_opportunity'),
    )

if not pattern_model_is_custom():
    urlpatterns += patterns('creme.commercial.views.act',
        url(r'^objective_patterns$',                            'listview_objective_pattern',   name='commercial__list_patterns'),
        url(r'^objective_pattern/add$',                         'add_objective_pattern',        name='commercial__create_pattern'),
        url(r'^objective_pattern/edit/(?P<objpattern_id>\d+)$', 'edit_objective_pattern',       name='commercial__edit_pattern'),
        url(r'^objective_pattern/(?P<objpattern_id>\d+)$',      'objective_pattern_detailview', name='commercial__view_pattern'), #TODO: a separated file for pattern ???
    )

if not strategy_model_is_custom():
    urlpatterns += patterns('creme.commercial.views.strategy',
        url(r'^strategies$',                         'listview',   name='commercial__list_strategies'),
        url(r'^strategy/add$',                       'add',        name='commercial__create_strategy'),
        url(r'^strategy/edit/(?P<strategy_id>\d+)$', 'edit',       name='commercial__edit_strategy'),
        url(r'^strategy/(?P<strategy_id>\d+)$',      'detailview', name='commercial__view_strategy'),
    )
