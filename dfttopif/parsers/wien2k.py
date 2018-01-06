from pypif.obj import *
from .base import DFTParser, Value_if_true
import os
from dftparse.util import *
from dftparse.wien2k.scf_parser import ScfParser
from dftparse.wien2k.scf2_parser import Scf2Parser
from dftparse.wien2k.absorp_parser import AbsorpParser
from dftparse.wien2k.eloss_parser import ElossParser
from dftparse.wien2k.epsilon_parser import EpsilonParser


class Wien2kParser(DFTParser):
    """
    Parser for Wien2k calculations
    """

    def get_name(self): return "Wien2k"

    def get_result_functions(self):
        base_results = super(Wien2kParser, self).get_result_functions()
        base_results["Optical conductivity xx (Re $\sigma_{xx}$)"] = "get_optical_conductivity_xx"
        base_results["Optical conductivity zz (Re $\sigma_{zz}$)"] = "get_optical_conductivity_zz"
        base_results["Absorption xx ($\\alpha_{xx}$)"] = "get_absorp_xx"
        base_results["Absorption zz ($\\alpha_{zz}$)"] = "get_absorp_zz"
        base_results["eloss$_{xx}$"] = "get_eloss_xx"
        base_results["eloss$_{zz}$"] = "get_eloss_zz"
        base_results["Re $\\varepsilon_{xx}$"] = "get_re_eps_xx"
        base_results["Im $\\varepsilon_{xx}$"] = "get_im_eps_xx"
        base_results["Re $\\varepsilon_{zz}$"] = "get_re_eps_zz"
        base_results["Im $\\varepsilon_{zz}$"] = "get_im_eps_zz"
        return base_results

    def test_if_from(self, directory):
        # Check whether it has a .scf file (analogous to an OUTCAR file)
        for filename in os.listdir(directory):
            if os.path.splitext(filename)[1] == ".scf":
                with open(os.path.join(directory, filename)) as fp:
                    for line in fp:
                        if "using WIEN2k" in line or ":ITE001:  1. ITERATION" in line:
                            return True
        return False

    def get_version_number(self):
        # Get version number from the .scf file
        for filename in os.listdir(self._directory):
            if os.path.splitext(filename)[1] == ".scf":

                with open(os.path.join(self._directory, filename)) as fp:

                    # look for line with ":LABEL3:"
                    for line in fp:
                        if ":LABEL3:" in line:
                            words = line.split()
                            return words[2].strip("WIEN2k_")

                # Error handling: version not found
                raise ValueError("Wien2k version not found")

    def get_total_energy(self):
        # Get data the .scf file
        for filename in os.listdir(self._directory):
            if os.path.splitext(filename)[1] == ".scf":
                file_path = os.path.join(self._directory, filename)
        if not file_path:
            return None

        parser = ScfParser()
        with open(file_path, "r") as fp:
            matches = [x for x in parser.parse(fp.readlines()) if "total energy" in x]
        if len(matches) == 0:
            return None
        total_energy = matches[-1]["total energy"]
        total_energy_units = matches[-1]["total energy units"]
        return Property(scalars=[Scalar(value=total_energy)], units=total_energy_units)

    def get_band_gap(self):
        # Get data the .scf2 file
        for filename in os.listdir(self._directory):
            if os.path.splitext(filename)[1] == ".scf2":
                file_path = os.path.join(self._directory, filename)
        if not file_path:
            return None

        parser = Scf2Parser()
        with open(file_path, "r") as fp:
            matches = [x for x in parser.parse(fp.readlines()) if "band gap" in x]
        if len(matches) == 0:
            return None
        band_gap = matches[-1]["band gap"]
        band_gap_units = matches[-1]["band gap units"]
        return Property(scalars=[Scalar(value=band_gap)], units=band_gap_units)

    @staticmethod
    def _get_wavelengths(energy_lst):
        return [Scalar(value=energy/1240) for energy in energy_lst]

    @staticmethod
    def _get_frequencies(energy_lst):
        return [Scalar(value=energy*2.418*10**14) for energy in energy_lst]

    @staticmethod
    def _get_scalars_lst(floats_lst):
        return [Scalar(value=num) for num in floats_lst]

    @staticmethod
    def _extract_file_data(directory, ext):
        # Get data from the .eloss file
        for filename in os.listdir(directory):
            if os.path.splitext(filename)[1] == ext:
                file_path = os.path.join(directory, filename)
        if not file_path:
            return None

        if ext == ".absorp":
            parser = AbsorpParser()
        elif ext == ".eloss":
            parser = ElossParser()
        elif ext == ".epsilon":
            parser = EpsilonParser()
        else:
            raise ValueError("Unrecognized extension: {}".format(ext))

        with open(file_path, "r") as fp:
            matches = [x for x in parser.parse(fp.readlines()) if "energy" in x]
        if len(matches) == 0:
            return None

        # Convert list of dics returned by dftparse to dic of lists
        non_empty_matches = remove_empty(matches)
        dic_of_lsts = transpose_list(non_empty_matches)

        return dic_of_lsts

    def get_optical_conductivity_xx(self):

        absorpdata_dic = Wien2kParser._extract_file_data(self._directory, ".absorp")

        # Get wavelengths and other scalar lists
        wavelengths = Wien2kParser._get_wavelengths(absorpdata_dic["energy"])
        re_sigma_xx = Wien2kParser._get_scalars_lst(absorpdata_dic["re_sigma_xx"])

        return Property(scalars=re_sigma_xx, units="1/(Ohm.cm)",
                        conditions=[Value(name="Wavelength", units="nm", scalars=wavelengths)])

    def get_optical_conductivity_zz(self):

        absorpdata_dic = Wien2kParser._extract_file_data(self._directory, ".absorp")

        # Get wavelengths and other scalar lists
        wavelengths = Wien2kParser._get_wavelengths(absorpdata_dic["energy"])
        re_sigma_xx = Wien2kParser._get_scalars_lst(absorpdata_dic["re_sigma_zz"])

        return Property(scalars=re_sigma_xx, units="1/(Ohm.cm)",
                        conditions=[Value(name="Wavelength", units="nm", scalars=wavelengths)])

    def get_absorp_xx(self):

        absorpdata_dic = Wien2kParser._extract_file_data(self._directory, ".absorp")

        # Get wavelengths and other scalar lists
        wavelengths = Wien2kParser._get_wavelengths(absorpdata_dic["energy"])
        re_sigma_xx = Wien2kParser._get_scalars_lst(absorpdata_dic["absorp_xx"])

        return Property(scalars=re_sigma_xx, units="10$^{4}$/cm",
                        conditions=[Value(name="Wavelength", units="nm", scalars=wavelengths)])

    def get_absorp_zz(self):

        absorpdata_dic = Wien2kParser._extract_file_data(self._directory, ".absorp")

        # Get wavelengths and other scalar lists
        wavelengths = Wien2kParser._get_wavelengths(absorpdata_dic["energy"])
        re_sigma_xx = Wien2kParser._get_scalars_lst(absorpdata_dic["absorp_zz"])

        return Property(scalars=re_sigma_xx, units="10$^{4}$/cm",
                        conditions=[Value(name="Wavelength", units="nm", scalars=wavelengths)])

    def get_eloss_xx(self):

        elossdata_dic = Wien2kParser._extract_file_data(self._directory, ".eloss")

        # Get wavelengths and other scalar lists
        wavelengths = Wien2kParser._get_wavelengths(elossdata_dic["energy"])
        eloss_xx = Wien2kParser._get_scalars_lst(elossdata_dic["eloss_xx"])

        return Property(scalars=eloss_xx,
                        conditions=[Value(name="Wavelength", units="nm", scalars=wavelengths)])

    def get_eloss_zz(self):

        elossdata_dic = Wien2kParser._extract_file_data(self._directory, ".eloss")

        # Get wavelengths and other scalar lists
        wavelengths = Wien2kParser._get_wavelengths(elossdata_dic["energy"])
        eloss_zz = Wien2kParser._get_scalars_lst(elossdata_dic["eloss_zz"])

        return Property(scalars=eloss_zz,
                        conditions=[Value(name="Wavelength", units="nm", scalars=wavelengths)])

    def get_re_eps_xx(self):

        epsdata_dic = Wien2kParser._extract_file_data(self._directory, ".epsilon")

        # Get frequency and other scalar lists
        frequencies = Wien2kParser._get_frequencies(epsdata_dic["energy"])
        re_eps_xx = Wien2kParser._get_scalars_lst(epsdata_dic["re_eps_xx"])

        return Property(scalars=re_eps_xx,
                        conditions=[Value(name="Frequency", units="Hz", scalars=frequencies)])

    def get_im_eps_xx(self):

        epsdata_dic = Wien2kParser._extract_file_data(self._directory, ".epsilon")

        # Get frequency and other scalar lists
        frequencies = Wien2kParser._get_frequencies(epsdata_dic["energy"])
        im_eps_xx = Wien2kParser._get_scalars_lst(epsdata_dic["im_eps_xx"])

        return Property(scalars=im_eps_xx,
                        conditions=[Value(name="Frequency", units="Hz", scalars=frequencies)])

    def get_re_eps_zz(self):

        epsdata_dic = Wien2kParser._extract_file_data(self._directory, ".epsilon")

        # Get frequency and other scalar lists
        frequencies = Wien2kParser._get_frequencies(epsdata_dic["energy"])
        re_eps_zz = Wien2kParser._get_scalars_lst(epsdata_dic["re_eps_zz"])

        return Property(scalars=re_eps_zz,
                        conditions=[Value(name="Frequency", units="Hz", scalars=frequencies)])

    def get_im_eps_zz(self):

        epsdata_dic = Wien2kParser._extract_file_data(self._directory, ".epsilon")

        # Get frequency and other scalar lists
        frequencies = Wien2kParser._get_frequencies(epsdata_dic["energy"])
        im_eps_zz = Wien2kParser._get_scalars_lst(epsdata_dic["im_eps_zz"])

        return Property(scalars=im_eps_zz,
                        conditions=[Value(name="Frequency", units="Hz", scalars=frequencies)])

    def uses_SOC(self):
        return None

    def is_relaxed(self):
        return None

    def get_U_settings(self):
        return None

    def get_vdW_settings(self):
        return None

    def get_pressure(self):
        return None

    def get_stresses(self):
        return None

    def get_dos(self):
        return None
