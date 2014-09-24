#!/usr/bin/python
#-------------------------------------------------------------------------------
# scripts/readelf.py
#
# A clone of 'readelf' in Python, based on the pyelftools library
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
import os, sys
import string

# For running from development directory. It should take precedence over the
# installed pyelftools.
sys.path.insert(0, '.')

from elftools import __version__
from elftools.common.exceptions import ELFError
from elftools.common.py3compat import (
        ifilter, byte2int, bytes2str, itervalues, str2bytes)
from elftools.elf.elffile import ELFFile
from elftools.elf.dynamic import DynamicSection

from elftools.elf.sections import SymbolTableSection
from elftools.elf.gnuversions import (
    GNUVerSymSection, GNUVerDefSection,
    GNUVerNeedSection,
    )
from elftools.elf.descriptions import (
    describe_ei_class, describe_ei_data, describe_ei_version,
    describe_ei_osabi, describe_e_type, describe_e_machine,
    describe_e_version_numeric, describe_p_type, describe_p_flags,
    describe_sh_type, describe_sh_flags,
    describe_symbol_type, describe_symbol_bind, describe_symbol_visibility,
    describe_symbol_shndx, describe_reloc_type, describe_dyn_tag,
    describe_ver_flags,
    )
from elftools.elf.constants import E_FLAGS


class ReadElf(object):
    """ display_* methods are used to emit output into the output stream
    """
    def __init__(self, file):
        """ file:
                stream object with the ELF file to read
            output:
                store string into self._emtline
        """
        self.elffile = ELFFile(file)
        self._versioninfo = None
        # Lazily initialized if a debug dump is requested
        self.display_str = ""

    def display_file_header(self):
        """ Display the ELF file header
        """
        self.display_str= ""
        self.__emitline('ELF Header:')
        self.__emit('  Magic:   ')
        self.__emitline(' '.join('%2.2x' % byte2int(b)
                                    for b in self.elffile.e_ident_raw))
        header = self.elffile.header
        e_ident = header['e_ident']
        self.__emitline('  Class:                             %s' %
                describe_ei_class(e_ident['EI_CLASS']))
        self.__emitline('  Data:                              %s' %
                describe_ei_data(e_ident['EI_DATA']))
        self.__emitline('  Version:                           %s' %
                describe_ei_version(e_ident['EI_VERSION']))
        self.__emitline('  OS/ABI:                            %s' %
                describe_ei_osabi(e_ident['EI_OSABI']))
        self.__emitline('  ABI Version:                       %d' %
                e_ident['EI_ABIVERSION'])
        self.__emitline('  Type:                              %s' %
                describe_e_type(header['e_type']))
        self.__emitline('  Machine:                           %s' %
                describe_e_machine(header['e_machine']))
        self.__emitline('  Version:                           %s' %
                describe_e_version_numeric(header['e_version']))
        self.__emitline('  Entry point address:               %s' %
                self._format_hex(header['e_entry']))
        self.__emit('  Start of program headers:          %s' %
                header['e_phoff'])
        self.__emitline(' (bytes into file)')
        self.__emit('  Start of section headers:          %s' %
                header['e_shoff'])
        self.__emitline(' (bytes into file)')
        self.__emitline('  Flags:                             %s%s' %
                (self._format_hex(header['e_flags']),
                self.decode_flags(header['e_flags'])))
        self.__emitline('  Size of this header:               %s (bytes)' %
                header['e_ehsize'])
        self.__emitline('  Size of program headers:           %s (bytes)' %
                header['e_phentsize'])
        self.__emitline('  Number of program headers:         %s' %
                header['e_phnum'])
        self.__emitline('  Size of section headers:           %s (bytes)' %
                header['e_shentsize'])
        self.__emitline('  Number of section headers:         %s' %
                header['e_shnum'])
        self.__emitline('  Section header string table index: %s' %
                header['e_shstrndx'])
        return self.display_str

    def get_basic_info():
        pass

    def decode_flags(self, flags):
        description = ""
        if self.elffile['e_machine'] == "EM_ARM":
            if flags & E_FLAGS.EF_ARM_HASENTRY:
                description += ", has entry point"

            version = flags & E_FLAGS.EF_ARM_EABIMASK
            if version == E_FLAGS.EF_ARM_EABI_VER5:
                description += ", Version5 EABI"
        return description

    def lookup_symbol(self, symName, quick_lookup = True):
        """ Display the symbol tables contained in the file
        """
        self._init_versioninfo()
        self.display_str = ""
        founded = False
        for section in self.elffile.iter_sections():
            if not isinstance(section, SymbolTableSection):
                continue

            if section['sh_entsize'] == 0:
                self.__emitline("\nSymbol table '%s' has a sh_entsize of zero!" % (
                    bytes2str(section.name)))
                continue

            self.__emitline("\nSymbol table '%s' contains %s entries:" % (
                bytes2str(section.name), section.num_symbols()))

            if self.elffile.elfclass == 32:
                self.__emitline('   Num:    Value  Size Type    Bind   Vis      Ndx Name\n')
            else: # 64
                self.__emitline('   Num:    Value          Size Type    Bind   Vis      Ndx Name\n')

            for nsym, symbol in enumerate(section.iter_symbols()):
                version_info = ''
                if symbol.name == "":
                    continue
                if quick_lookup:
                    if not (symbol.name == symName):
                        continue
                # take a deep compare
                elif symbol.name not in symName and symName not in symbol.name:
                    continue
                founded = True
                # readelf doesn't display version info for Solaris versioning
                if (section['sh_type'] == 'SHT_DYNSYM' and
                        self._versioninfo['type'] == 'GNU'):
                    version = self._symbol_version(nsym)
                    if (version['name'] != bytes2str(symbol.name) and
                        version['index'] not in ('VER_NDX_LOCAL',
                                                 'VER_NDX_GLOBAL')):
                        if version['filename']:
                            # external symbol
                            version_info = '@%(name)s (%(index)i)' % version
                        else:
                            # internal symbol
                            if version['hidden']:
                                version_info = '@%(name)s[hidden]' % version
                            else:
                                version_info = '@@%(name)s' % version

                # symbol names are truncated to 25 chars, similarly to readelf
                self.__emitline('%6d: %s %5d %-7s %-6s %-7s %4s %.25s%s' % (
                    nsym,
                    self._format_hex(
                        symbol['st_value'], fullhex=True, lead0x=False),
                    symbol['st_size'],
                    describe_symbol_type(symbol['st_info']['type']),
                    describe_symbol_bind(symbol['st_info']['bind']),
                    describe_symbol_visibility(symbol['st_other']['visibility']),
                    describe_symbol_shndx(symbol['st_shndx']),
                    bytes2str(symbol.name),
                    version_info))
                # self.__emitline('---'*4 + "section name:" +section.name + '---'*4)
                if quick_lookup:
                    return self.display_str
        if founded:
            return self.display_str
        else:
            return "NotFound..."

    # not use
    def display_all_symbol_tables(self):
        """ Display the symbol tables contained in the file
        """
        self._init_versioninfo()
        self.display_str = ""
        for section in self.elffile.iter_sections():
            if not isinstance(section, SymbolTableSection):
                continue

            if section['sh_entsize'] == 0:
                self.__emitline("\nSymbol table '%s' has a sh_entsize of zero!" % (
                    bytes2str(section.name)))
                continue

            self.__emitline("\nSymbol table '%s' contains %s entries:" % (
                bytes2str(section.name), section.num_symbols()))

            if self.elffile.elfclass == 32:
                self.__emitline('   Num:    Value  Size Type    Bind   Vis      Ndx Name')
            else: # 64
                self.__emitline('   Num:    Value          Size Type    Bind   Vis      Ndx Name')

            for nsym, symbol in enumerate(section.iter_symbols()):

                version_info = ''
                # readelf doesn't display version info for Solaris versioning
                if (section['sh_type'] == 'SHT_DYNSYM' and
                        self._versioninfo['type'] == 'GNU'):
                    version = self._symbol_version(nsym)
                    if (version['name'] != bytes2str(symbol.name) and
                        version['index'] not in ('VER_NDX_LOCAL',
                                                 'VER_NDX_GLOBAL')):
                        if version['filename']:
                            # external symbol
                            version_info = '@%(name)s (%(index)i)' % version
                        else:
                            # internal symbol
                            if version['hidden']:
                                version_info = '@%(name)s' % version
                            else:
                                version_info = '@@%(name)s' % version

                # symbol names are truncated to 25 chars, similarly to readelf
                self.__emitline('%6d: %s %5d %-7s %-6s %-7s %4s %.25s%s' % (
                    nsym,
                    self._format_hex(
                        symbol['st_value'], fullhex=True, lead0x=False),
                    symbol['st_size'],
                    describe_symbol_type(symbol['st_info']['type']),
                    describe_symbol_bind(symbol['st_info']['bind']),
                    describe_symbol_visibility(symbol['st_other']['visibility']),
                    describe_symbol_shndx(symbol['st_shndx']),
                    bytes2str(symbol.name),
                    version_info))
        return self.display_str

    def _format_hex(self, addr, fieldsize=None, fullhex=False, lead0x=True,
                    alternate=False):
        """ Format an address into a hexadecimal string.

            fieldsize:
                Size of the hexadecimal field (with leading zeros to fit the
                address into. For example with fieldsize=8, the format will
                be %08x
                If None, the minimal required field size will be used.

            fullhex:
                If True, override fieldsize to set it to the maximal size
                needed for the elfclass

            lead0x:
                If True, leading 0x is added

            alternate:
                If True, override lead0x to emulate the alternate
                hexadecimal form specified in format string with the #
                character: only non-zero values are prefixed with 0x.
                This form is used by readelf.
        """
        if alternate:
            if addr == 0:
                lead0x = False
            else:
                lead0x = True
                fieldsize -= 2

        s = '0x' if lead0x else ''
        if fullhex:
            fieldsize = 8 if self.elffile.elfclass == 32 else 16
        if fieldsize is None:
            field = '%x'
        else:
            field = '%' + '0%sx' % fieldsize
        return s + field % addr

    def _init_versioninfo(self):
        """ Search and initialize informations about version related sections
            and the kind of versioning used (GNU or Solaris).
        """
        if self._versioninfo is not None:
            return

        self._versioninfo = {'versym': None, 'verdef': None,
                             'verneed': None, 'type': None}

        for section in self.elffile.iter_sections():
            if isinstance(section, GNUVerSymSection):
                self._versioninfo['versym'] = section
            elif isinstance(section, GNUVerDefSection):
                self._versioninfo['verdef'] = section
            elif isinstance(section, GNUVerNeedSection):
                self._versioninfo['verneed'] = section
            elif isinstance(section, DynamicSection):
                for tag in section.iter_tags():
                    if tag['d_tag'] == 'DT_VERSYM':
                        self._versioninfo['type'] = 'GNU'
                        break

        if not self._versioninfo['type'] and (
                self._versioninfo['verneed'] or self._versioninfo['verdef']):
            self._versioninfo['type'] = 'Solaris'

    def _symbol_version(self, nsym):
        """ Return a dict containing information on the
                   or None if no version information is available
        """
        self._init_versioninfo()

        symbol_version = dict.fromkeys(('index', 'name', 'filename', 'hidden'))

        if (not self._versioninfo['versym'] or
                nsym >= self._versioninfo['versym'].num_symbols()):
            return None

        symbol = self._versioninfo['versym'].get_symbol(nsym)
        index = symbol.entry['ndx']
        if not index in ('VER_NDX_LOCAL', 'VER_NDX_GLOBAL'):
            index = int(index)

            if self._versioninfo['type'] == 'GNU':
                # In GNU versioning mode, the highest bit is used to
                # store wether the symbol is hidden or not
                if index & 0x8000:
                    index &= ~0x8000
                    symbol_version['hidden'] = True

            if (self._versioninfo['verdef'] and
                    index <= self._versioninfo['verdef'].num_versions()):
                _, verdaux_iter = \
                        self._versioninfo['verdef'].get_version(index)
                symbol_version['name'] = bytes2str(next(verdaux_iter).name)
            else:
                verneed, vernaux = \
                        self._versioninfo['verneed'].get_version(index)
                symbol_version['name'] = bytes2str(vernaux.name)
                symbol_version['filename'] = bytes2str(verneed.name)

        symbol_version['index'] = index
        return symbol_version

    def __emit(self, s=''):
        """ Emit an object to output """
        self.display_str += str(s)

    def __emitline(self, s=''):
        """ Emit an object to output, followed by a newline """
        self.display_str = self.display_str + str(s) + '\n'

def do_quick_lookupsymbol(symName, fd):
    readelf = ReadElf(fd)
    return readelf.lookup_symbol(symName,)

def do_deep_lookupsymbol(symName, fd):
    readelf = ReadElf(fd)
    return readelf.lookup_symbol(symName, quick_lookup=False)

def do_get_basic_elf_info(fd):
    readelf = ReadElf(fd)
    return readelf.display_file_header()


#-------------------------------------------------------------------------------
if __name__ == '__main__':
    #profile_main()
    with open(sys.argv[1], 'rb') as file:
        try:
            readelf = ReadElf(file)
            basic_info = readelf.display_file_header()
            #function_info = readelf.display_symbol_tables()
            print basic_info
            print readelf.lookup_symbol("prepare_creds",quick_lookup=False)
        except ELFError as ex:
            sys.stderr.write('ELF error: %s\n' % ex)


