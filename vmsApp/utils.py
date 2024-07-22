# utils.py
import jpype
from jpype import java, JClass, JString
from django.db import connection
from .models import Visitors

def generate_report(output_format='pdf', parameters=None):
    jpype.startJVM(jpype.getDefaultJVMPath())

    try:
        JasperCompileManager = JClass('net.sf.jasperreports.engine.JasperCompileManager')
        JasperFillManager = JClass('net.sf.jasperreports.engine.JasperFillManager')
        JasperExportManager = JClass('net.sf.jasperreports.engine.JasperExportManager')

        # Update the JRXML file path
        compiled_report = JasperCompileManager.compileReport('C:/Users/dell/JaspersoftWorkspace/MyReports/table.jrxml')

        # Fetch data from the Visitors model
        visitors = Visitors.objects.all().values()
        jasper_data_source = java.util.ArrayList()
        for visitor in visitors:
            jasper_data_source.add(java.util.HashMap(visitor))

        filled_report = JasperFillManager.fillReport(compiled_report, parameters, jasper_data_source)

        # Update the output file path
        output_file = 'C:/path/to/output/report.' + output_format
        JasperExportManager.exportReportToPdfFile(filled_report, output_file)

        return output_file

    finally:
        jpype.shutdownJVM()
