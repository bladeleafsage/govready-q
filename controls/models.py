import os
import json
from django.db import models
from guardian.shortcuts import (assign_perm, get_objects_for_user,
                                get_perms_for_model, get_user_perms,
                                get_users_with_perms, remove_perm)
from .oscal import Catalogs, Catalog


BASELINE_PATH = os.path.join(os.path.dirname(__file__),'data','baselines')

class Statement(models.Model):
    sid = models.CharField(max_length=100, help_text="Statement identifier such as OSCAL formatted Control ID", unique=False, blank=False, null=False)
    sid_class = models.CharField(max_length=200, help_text="Statement identifier 'class' such as '800-53rev4' or other OSCAL catalog name Control ID ", unique=False, blank=False, null=False)
    body = models.TextField(help_text="The statement itself", unique=False, blank=True, null=True)
    statement_type = models.CharField(max_length=150, help_text="Statement type", unique=False, blank=True, null=True)
    remarks = models.TextField(help_text="The statement itself", unique=False, blank=True, null=True)
    version = models.CharField(max_length=20, help_text="Optional version number", unique=False, blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True, db_index=True)
    updated = models.DateTimeField(auto_now_add=True, db_index=True)

    parent = models.ForeignKey('self', help_text="Optional version number", on_delete=models.SET_NULL, blank=True, null=True)
    producer_element = models.ForeignKey('Element', related_name='statements_produced', on_delete=models.SET_NULL, blank=True, null=True, help_text="The element producing this statement. ")
    consumer_element = models.ForeignKey('Element', related_name='statements_consumed', on_delete=models.SET_NULL, blank=True, null=True, help_text="The element the statement is about. ")
    mentioned_elements = models.ManyToManyField('Element', related_name='statements_mentioning', blank=True, help_text="All elements mentioned in a statement; elements with a first degree relationship to the statement.")

    class Meta:
        permissions = [
            ('can_grant_smt_owner_permission', 'Grant a user statement owner permission'),
        ]

    def __str__(self):
        return "'%s %s %s id=%d'" % (self.statement_type, self.sid, self.sid_class, self.id)

    def __repr__(self):
        # For debugging.
        return "'%s %s %s id=%d'" % (self.statement_type, self.sid, self.sid_class, self.id)

    # TODO:
    #   - On Save be sure to replace any '\r\n' with '\n' added by round-tripping with excel

class Element(models.Model):
    name = models.CharField(max_length=250, help_text="Common name or acronym of the element", unique=True, blank=False, null=False)
    full_name =models.CharField(max_length=250, help_text="Full name of the element", unique=False, blank=True, null=True)
    description = models.CharField(max_length=255, help_text="Brief description of the Element", unique=False, blank=False, null=False)
    element_type = models.CharField(max_length=150, help_text="Statement type", unique=False, blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True, db_index=True)
    updated = models.DateTimeField(auto_now_add=True, db_index=True)

    # Notes
    # Retrieve Element controls where element is e to answer "What controls selected for a system?" (System is an element.)
    #    element_id = 8
    #    e = Element.objects.get(id=element_id);
    #    e.controls.all()
    #    # returns <QuerySet ['ac-2 id=1', 'ac-3 id=2', 'au-2 id=3']>
    #
    # Retrieve statements
    #    e.statements_consumed.all()
    #
    # Retrieve statements that are control implementations
    #    e.statements_consumed.filter(statement_type="control_implementation")


    def __str__(self):
        return "'%s id=%d'" % (self.name, self.id)

    def __repr__(self):
        # For debugging.
        return "'%s id=%d'" % (self.name, self.id)

    def assign_baseline_controls(self, user, baselines_key, baseline_name):
        """Assign set of controls from baseline to an element"""

        # Usage
            # s = System.objects.get(pk=20)
            # s.root_element.assign_baseline_controls('NIST_SP-800-53_rev4', 'low')

        can_assign_controls = user.has_perm('edit_system', self.system)
        # Does user have edit permissions on system?
        if  can_assign_controls:
            from controls.models import Baselines
            bs = Baselines()
            controls = bs.get_baseline_controls(baselines_key, baseline_name)
            for oscal_ctl_id in controls:
                ec = ElementControl(element=self, oscal_ctl_id=oscal_ctl_id, oscal_catalog_key=baselines_key)
                ec.save()
        else:
            print("User does not have permission to assign selected controls to element's system.")
            return False

    @property
    def selected_controls_oscal_ctl_ids(self):
        """Return array of selectecd controls oscal ids"""
        # oscal_ids = self.controls.all()
        oscal_ctl_ids = [control.oscal_ctl_id for control in self.controls.all()]
        return oscal_ctl_ids

class ElementControl(models.Model):
    element = models.ForeignKey(Element, related_name="controls", on_delete=models.CASCADE, help_text="The Element (e.g., System, Component, Host) to which controls are associated.")
    oscal_ctl_id = models.CharField(max_length=20, help_text="OSCAL formatted Control ID (e.g., au-2.3)", blank=True, null=True)
    oscal_catalog_key = models.CharField(max_length=100, help_text="Catalog key from which catalog file can be derived (e.g., 'NIST_SP-800-53_rev4')", blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True, db_index=True)
    updated = models.DateTimeField(auto_now=True, db_index=True)

    # Notes
    # from controls.oscal import *;from controls.models import *;
    #     e = Element.objects.get(id=8);
    #     e.name;
    #     ecq = ElementControl.objects.filter(element=e);
    #     ec = ecq[0]
    #     ec.oscal_catalog_key
    #     cg = Catalog(ec.oscal_catalog_key)
    #     print(cg.get_flattened_control_as_dict(cg.get_control_by_id(ec.oscal_ctl_id)))
    #
    #     # Get the flattened oscal control information
    #     ec.get_flattened_oscal_control_as_dict()
    #     # Get Implementation statement if it exists
    #     ec.get_flattened_impl_smt_as_dict()
    #
    #     # Get an element/system by it's element id
    #     e = Element.objects.get(id=8);
    #     e.name;
    #     # Get all ElementControls for the Element
    #     ec_list = ElementControl.objects.filter(element=e);
    #     for ec in ec_list:
    #       print("OSCAL CONTROL")
    #       print(ec.get_flattened_oscal_control_as_dict())
    #       print("Implementation Statement")
    #       print(ec.get_flattened_impl_smt_as_dict())

    class Meta:
        unique_together = [('element', 'oscal_ctl_id', 'oscal_catalog_key')]

    def __str__(self):
        return "'%s id=%d'" % (self.oscal_ctl_id, self.id)

    def __repr__(self):
        # For debugging.
        return "'%s id=%d'" % (self.oscal_ctl_id, self.id)

    def get_controls_by_element(self, element):
        query_set = self.objects.filter(element=element)
        selected_controls = {}
        for cl in query_set:
            selected_controls[cl['oscal_ctl_id']] = {'oscal_ctl_id': cl['oscal_ctl_id'], 'oscal_catalog_key': cl['oscal_catalog_key']}
        return selected_controls

    def get_flattened_oscal_control_as_dict(self):
        cg = Catalog.GetInstance(catalog_key=self.oscal_catalog_key)
        return cg.get_flattened_control_as_dict(cg.get_control_by_id(self.oscal_ctl_id))

    # def get_flattened_impl_smt_as_dict(self):
    #     """Return the implementation statement for this ElementControl combination"""
    #     # For development let's hardcode what we return
    #     impl_smt = {"sid": "impl_smt sid", "body": "This is the statement itself"}
    #     # Error checking
    #     return impl_smt

class System(models.Model):
    root_element = models.ForeignKey(Element, related_name="system", on_delete=models.CASCADE, help_text="The Element that is this System. Element must be type [Application, General Support System]")
    fisma_id = models.CharField(max_length=40, help_text="The FISMA Id of the system", unique=False, blank=True, null=True)

    # Notes
    # Retrieve system implementation statements
    #   system = System.objects.get(pk=2)
    #   system.root_element.statements_consumed.filter(statement_type="control_implementation")
    #
    # Retrieve system common controls statements
    #   system = System.objects.get(pk=2)
    #   system.root_element.common_controls.all()[0].common_control.legacy_imp_smt
    #   system.root_element.common_controls.all()[0].common_control.body
    #

    def __str__(self):
        return "'System %s id=%d'" % (self.root_element.name, self.id)

    def __repr__(self):
        # For debugging.
        return "'System %s id=%d'" % (self.root_element.name, self.id)

    # @property
    # def statements_consumed(self):
    #     smts = self.root_element.statements_consumed.all()
    #     return smts

    @property
    def smts_common_controls_as_dict(self):
        common_controls = self.root_element.common_controls.all()
        smts_as_dict = {}
        for cc in common_controls:
            if cc.common_control.oscal_ctl_id in smts_as_dict:
                smts_as_dict[cc.common_control.oscal_ctl_id].append(cc)
            else:
                smts_as_dict[cc.common_control.oscal_ctl_id] = [cc]
        return smts_as_dict

    @property
    def smts_control_implementation_as_dict(self):
        smts = self.root_element.statements_consumed.filter(statement_type="control_implementation")
        smts_as_dict = {}
        for smt in smts:
            if smt.sid in smts_as_dict:
                smts_as_dict[smt.sid]['control_impl_smts'].append(smt)
            else:
                smts_as_dict[smt.sid] = {"control_impl_smts": [smt], "common_controls": [], "combined_smt": ""}
        return smts_as_dict

    @property
    def control_implementation_as_dict(self):
        # Get the smts_control_implementations
        smts = self.root_element.statements_consumed.filter(statement_type="control_implementation")
        smts_as_dict = {}
        for smt in smts:
            if smt.sid in smts_as_dict:
                smts_as_dict[smt.sid]['control_impl_smts'].append(smt)
            else:
                smts_as_dict[smt.sid] = {"control_impl_smts": [smt], "common_controls": [], "combined_smt": ""}
            # Build combined statement
            smts_as_dict[smt.sid]['combined_smt'] += "{}\n{}\n\n".format(smt.producer_element.name, smt.body)

        # Add in the common controls
        for cc in self.root_element.common_controls.all():
            if cc.common_control.oscal_ctl_id in smts_as_dict:
                smts_as_dict[smt.sid]['common_controls'].append(cc)
            else:
                smts_as_dict[cc.common_control.oscal_ctl_id] = {"control_impl_smts": [], "common_controls": [cc], "combined_smt": ""}
            # Build combined statement
            smts_as_dict[cc.common_control.oscal_ctl_id]['combined_smt'] += "{}\n{}\n\n".format(cc.common_control.name, cc.common_control.body)
        return smts_as_dict

    def get_producer_elements(self):
        smts = self.root_element.statements_consumed.all()
        components = set()
        for smt in smts:
            if smt.producer_element:
                components.add(smt.producer_element)
        return components

    producer_elements = property(get_producer_elements)

class CommonControlProvider(models.Model):
    name = models.CharField(max_length=150, help_text="Name of the CommonControlProvider", unique=False)
    description = models.CharField(max_length=255, help_text="Brief description of the CommonControlProvider", unique=False)

    def __str__(self):
        return self.name

class CommonControl(models.Model):
    name = models.CharField(max_length=150, help_text="Name of the CommonControl", unique=False, blank=True, null=True)
    description = models.CharField(max_length=255, help_text="Brief description of the CommonControlProvider", unique=False)
    oscal_ctl_id = models.CharField(max_length=20, help_text="OSCAL formatted Control ID (e.g., au-2.3)", blank=True, null=True)
    legacy_imp_smt = models.TextField(help_text="Legacy large implementation statement", unique=False, blank=True, null=True,)
    common_control_provider =  models.ForeignKey(CommonControlProvider, on_delete=models.CASCADE)

    def __str__(self):
        return self.name

class ElementCommonControl(models.Model):
    element = models.ForeignKey(Element, related_name="common_controls", on_delete=models.CASCADE, help_text="The Element (e.g., System, Component, Host) to which common controls are associated.")
    common_control = models.ForeignKey(CommonControl, related_name="element_common_control", on_delete=models.CASCADE, help_text="The Common Control for this association.")
    oscal_ctl_id = models.CharField(max_length=20, help_text="OSCAL formatted Control ID (e.g., au-2.3)", blank=True, null=True)
    oscal_catalog_key = models.CharField(max_length=100, help_text="Catalog key from which catalog file can be derived (e.g., 'NIST_SP-800-53_rev4')", blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True, db_index=True)
    updated = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        unique_together = [('element', 'common_control', 'oscal_ctl_id', 'oscal_catalog_key')]

    def __str__(self):
        return "'%s %s %s id=%d'" % (self.element, self.common_control, self.oscal_ctl_id, self.id)

    def __repr__(self):
        # For debugging.
        return "'%s %s %s id=%d'" % (self.element, self.common_control, self.oscal_ctl_id, self.id)

class Baselines (object):
    """Represent list of baselines"""
    def __init__(self):
        global BASELINE_PATH
        self.file_path = BASELINE_PATH
        self.baselines_keys = self._list_keys()
        # self.index = self._build_index()

        # Usage
            # from controls.models import Baselines
            # bs = Baselines()
            # bs.baselines_keys
            # bs53 = bs._load_json('NIST_SP-800-53_rev4')
            # bs53['moderate']['controls']
            # # Returns ['ac-1', 'ac-2', 'ac-2.1', 'ac-2.2', ...]
            # bs.get_baseline_controls('NIST_SP-800-53_rev4', 'moderate')

    def _list_files(self):
        return [
            'NIST_SP-800-53_rev4_baselines.json',
            # 'NIST_SP-800-53_rev5_baselines.json',
            'NIST_SP-800-171_rev1_baselines.json'
        ]

    def _list_keys(self):
        return [
            'NIST_SP-800-53_rev4',
            # 'NIST_SP-800-53_rev5',
            'NIST_SP-800-171_rev1'
        ]

    def _load_json(self, baselines_key):
        """Read baseline file - JSON"""
        # TODO Escape baselines_key
        self.data_file = baselines_key + "_baselines.json"
        data_file = os.path.join(self.file_path, self.data_file)
        # Does file exist?
        if not os.path.isfile(data_file):
            print("ERROR: {} does not exist".format(data_file))
            return False
        # Load file as json
        try:
            with open(data_file, 'r') as json_file:
                data = json.load(json_file)
            return data
        except:
            print("ERROR: {} could not be read or could not be read as json".format(data_file))
            return False

    def get_baseline_controls(self, baselines_key, baseline_name):
        """Return baseline's control OSCAL control ids given baselines key and baseline name"""
        if baselines_key in self.baselines_keys:
            data = self._load_json(baselines_key)
        else:
            print("Requested baselines_key not found in baselines_key data file")
            return False
        if baseline_name in data.keys():
            return data[baseline_name]['controls']
        else:
            print("Requested baseline name not found in baselines_key data file")
            return False

    @property
    def body(self):
        return self.legacy_imp_smt
