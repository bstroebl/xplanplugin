#!/bin/bash
createdb xplan
psql xplan -c "create extension postgis"
psql xplan -a -f /home/user/Downloads/xplanPostGIS-5.1/XP_Basisschema.sql > XP_Basisschema.log 2>&1
psql xplan -a -f /home/user/Downloads/xplanPostGIS-5.1/BP_Fachschema_BPlan.sql > BP_Fachschema_BPlan.log 2>&1
psql xplan -a -f /home/user/Downloads/xplanPostGIS-5.1/FP_Fachschema_FPlan.sql > FP_Fachschema_FPlan.log 2>&1
psql xplan -a -f /home/user/Downloads/xplanPostGIS-5.1/LP_Fachschema_LPlan.sql > LP_Fachschema_LPlan.log 2>&1
psql xplan -a -f /home/user/Downloads/xplanPostGIS-5.1/RP_Fachschema_Regionalplan.sql > RP_Fachschema_Regionalplan.log 2>&1
psql xplan -a -f /home/user/Downloads/xplanPostGIS-5.1/SO_Fachschema_SonstigePlaene.sql > SO_Fachschema_SonstigePlaene.log 2>&1
psql xplan -a -f /home/user/Downloads/xplanPostGIS-5.1/QGIS.sql > QGIS.log 2>&1
psql xplan -a -f /home/user/Downloads/xplanPostGIS-5.1/XP_QGIS.sql > XP_QGIS.log 2>&1
psql xplan -a -f /home/user/Downloads/xplanPostGIS-5.1/BP_QGIS.sql > BP_QGIS.log 2>&1
psql xplan -a -f /home/user/Downloads/xplanPostGIS-5.1/FP_QGIS.sql > FP_QGIS.log 2>&1
psql xplan -a -f /home/user/Downloads/xplanPostGIS-5.1/LP_QGIS.sql > LP_QGIS.log 2>&1
psql xplan -a -f /home/user/Downloads/xplanPostGIS-5.1/SO_QGIS.sql > SO_QGIS.log 2>&1
psql xplan -a -f /home/user/Downloads/xplanPostGIS-5.1/layer_styles_QGIS.sql > layer_styles_QGIS.log 2>&1
