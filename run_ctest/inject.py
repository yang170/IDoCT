"""inject parameter, values into sw config"""

import fileinput
import sys
import xml.etree.ElementTree as ET
import yaml
import shutil

sys.path.append("..")
from ctest_const import *

from program_input import p_input

project = p_input["project"]

def inject_config(param_value_pairs):
    for p, v in param_value_pairs.items():
        print(">>>>[ctest_core] injecting {} with value {}".format(p, v))

    if project in [ZOOKEEPER, ALLUXIO]:
        for inject_path in INJECTION_PATH[project]:
            print(">>>>[ctest_core] injecting into file: {}".format(inject_path))
            file = open(inject_path, "w")
            for p, v in param_value_pairs.items():
                file.write(p + "=" + v + "\n")
            file.close()
    elif project in [HCOMMON, HDFS, HBASE]:
        conf = ET.Element("configuration")
        for p, v in param_value_pairs.items():
            prop = ET.SubElement(conf, "property")
            name = ET.SubElement(prop, "name")
            value = ET.SubElement(prop, "value")
            name.text = p
            value.text = v
        for inject_path in INJECTION_PATH[project]:
            print(">>>>[ctest_core] injecting into file: {}".format(inject_path))
            file = open(inject_path, "wb")
            file.write(str.encode("<?xml version=\"1.0\"?>\n<?xml-stylesheet type=\"text/xsl\" href=\"configuration.xsl\"?>\n"))
            file.write(ET.tostring(conf))
            file.close()
    elif project in [DROPWIZARD_HEALTH]:
        HEALTH_PATH_IDX = 0
        HEALTH_CHECK_PATH_IDX = 1
        HEALTH_CHECK_JAVA_CODE_PATH_IDX = 2
        SCHEDULE_PATH_IDX = 3

        health_conf = yaml.full_load(open(INJECTION_PATH[DROPWIZARD_HEALTH][HEALTH_PATH_IDX], "r"))
        health_check_conf = yaml.full_load(open(INJECTION_PATH[DROPWIZARD_HEALTH][HEALTH_CHECK_PATH_IDX], "r"))
        schedule_conf = yaml.full_load(open(INJECTION_PATH[DROPWIZARD_HEALTH][SCHEDULE_PATH_IDX], "r"))

        for p, v in param_value_pairs.items():
            if v == 'true' or v == 'True':
                v = True
            elif v == 'false' or v == 'False':
                v = False

            p_expanded = p.split('.')
            if (len(p_expanded) < 2 or p_expanded[0] != 'health'):
                sys.exit(">>>>[ctest_core] invalid parameter {}".format(p))
            
            if (len(p_expanded) == 2):
                # configuring health.param_name
                param_name_idx = 1
                health_conf[p_expanded[param_name_idx]] = v
            elif (len(p_expanded) == 3):
                # configuring health.healthChecks.param_name
                param_name_idx = 2
                health_conf['healthChecks'][0][p_expanded[param_name_idx]] = v
                health_check_conf[p_expanded[param_name_idx]] = v

                code_injection_line_number = DEFAULT_CONF_LINE_NUMBER[DROPWIZARD_HEALTH][p]

                if code_injection_line_number is not None:
                    for line in fileinput.input(INJECTION_PATH[DROPWIZARD_HEALTH][HEALTH_CHECK_JAVA_CODE_PATH_IDX], inplace=True):
                        if fileinput.filelineno() == code_injection_line_number:
                            format_string = DEFAULT_CONF_CODE_FORMAT_STRING[DROPWIZARD_HEALTH][p]
                            if p_expanded[param_name_idx] == "type":
                                if v == "ready":
                                    sys.stdout.write(format_string.format("HealthCheckType.READY"))
                                else:
                                     sys.stdout.write(format_string.format("HealthCheckType.ALIVE"))
                            else:
                                sys.stdout.writelines(format_string.format(v))
                        else:
                            sys.stdout.write(line)
                                    

            elif (len(p_expanded) == 4):
                # configuring health.healthChecks.schedule.param_name
                param_name_idx = 3
                health_conf['healthChecks'][0]['schedule'] = dict()
                health_conf['healthChecks'][0]['schedule'][p_expanded[param_name_idx]] = v
                schedule_conf[p_expanded[param_name_idx]] = v

        with open(INJECTION_PATH[DROPWIZARD_HEALTH][HEALTH_PATH_IDX], 'w') as inject_conf:
            inject_conf.write(yaml.dump(health_conf, sort_keys=False))
        
        with open(INJECTION_PATH[DROPWIZARD_HEALTH][HEALTH_CHECK_PATH_IDX], 'w') as inject_conf:
            inject_conf.write(yaml.dump(health_check_conf, sort_keys=False))

        with open(INJECTION_PATH[DROPWIZARD_HEALTH][SCHEDULE_PATH_IDX], 'w') as inject_conf:
            inject_conf.write(yaml.dump(schedule_conf, sort_keys=False))

    else:
        sys.exit(">>>>[ctest_core] value injection for {} is not supported yet".format(project))


def clean_conf_file(project):
    print(">>>> cleaning injected configuration from file")
    if project in [ZOOKEEPER, ALLUXIO]:
        for inject_path in INJECTION_PATH[project]:
            file = open(inject_path, "w")
            file.write("\n")
            file.close()
    elif project in [HCOMMON, HDFS, HBASE]:
        conf = ET.Element("configuration")
        for inject_path in INJECTION_PATH[project]:
            file = open(inject_path, "wb")
            file.write(str.encode("<?xml version=\"1.0\"?>\n<?xml-stylesheet type=\"text/xsl\" href=\"configuration.xsl\"?>\n"))
            file.write(ET.tostring(conf))
            file.close()
    elif project in [DROPWIZARD_HEALTH]:
        HEALTH_PATH_IDX = 0
        HEALTH_CHECK_PATH_IDX = 1
        HEALTH_CHECK_JAVA_CODE_PATH_IDX = 2
        SCHEDULE_PATH_IDX = 3

        health_default_conf = yaml.full_load(open(DEFAULT_CONF_FILE[DROPWIZARD_HEALTH][HEALTH_PATH_IDX], "r"))
        health_check_default_conf = yaml.full_load(open(DEFAULT_CONF_FILE[DROPWIZARD_HEALTH][HEALTH_CHECK_PATH_IDX], "r"))
        schedule_default_conf = yaml.full_load(open(DEFAULT_CONF_FILE[DROPWIZARD_HEALTH][SCHEDULE_PATH_IDX], "r"))

        with open(INJECTION_PATH[DROPWIZARD_HEALTH][HEALTH_PATH_IDX], 'w') as inject_conf:
            inject_conf.write(yaml.dump(health_default_conf, sort_keys=False))
        
        with open(INJECTION_PATH[DROPWIZARD_HEALTH][HEALTH_CHECK_PATH_IDX], 'w') as inject_conf:
            inject_conf.write(yaml.dump(health_check_default_conf, sort_keys=False))
        
        shutil.copy(DEFAULT_CONF_FILE[DROPWIZARD_HEALTH][HEALTH_CHECK_JAVA_CODE_PATH_IDX], INJECTION_PATH[DROPWIZARD_HEALTH][HEALTH_CHECK_JAVA_CODE_PATH_IDX])

        with open(INJECTION_PATH[DROPWIZARD_HEALTH][SCHEDULE_PATH_IDX], 'w') as inject_conf:
            inject_conf.write(yaml.dump(schedule_default_conf, sort_keys=False))
    else:
        sys.exit(">>>>[ctest_core] value injection for {} is not supported yet".format(project))
