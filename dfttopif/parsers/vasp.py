from pypif.obj import Property, Scalar

from .base import DFTParser, Value_if_true
import os
from ase.calculators.vasp import Vasp
from ase.io.vasp import read_vasp, read_vasp_out
from pypif.obj import Value, FileReference
from dftparse.vasp.outcar_parser import OutcarParser
from dftparse.vasp.eigenval_parser import EigenvalParser


class VaspParser(DFTParser):
    '''
    Parser for VASP calculations
    '''

    def get_name(self): return "VASP"
    
    def test_if_from(self, directory):
        # Check whether it has an INCAR file
        return os.path.isfile(os.path.join(directory, 'OUTCAR'))
        
    def get_output_structure(self):
        self.atoms = read_vasp_out(os.path.join(self._directory, 'OUTCAR'))
        return self.atoms

    def get_outcar(self):
        raw_path = os.path.join(self._directory, 'OUTCAR')
        if raw_path[0:2] == "./":
            raw_path = raw_path[2:]
        return Property(files=[FileReference(
            relative_path=raw_path
        )])

    def get_incar(self):
        raw_path = os.path.join(self._directory, 'INCAR')
        if raw_path[0:2] == "./":
            raw_path = raw_path[2:]
        return Value(files=[FileReference(
            relative_path=raw_path
        )])

    def get_poscar(self):
        raw_path = os.path.join(self._directory, 'POSCAR')
        if raw_path[0:2] == "./":
            raw_path = raw_path[2:]
        return Value(files=[FileReference(
            relative_path=raw_path
        )])

    def get_cutoff_energy(self):
        # Open up the OUTCAR
        with open(os.path.join(self._directory, 'OUTCAR'), 'r') as fp:
         # Look for ENCUT
            for line in fp:
                if "ENCUT" in line:
                    words = line.split()
                    return Value(scalars=[Scalar(value=float(words[2]))], units=words[3])
                
        # Error handling: ENCUT not found
        raise Exception('ENCUT not found')

    @Value_if_true
    def uses_SOC(self):
        # Open up the OUTCAR
        with open(os.path.join(self._directory, 'OUTCAR')) as fp:
        
            #look for LSORBIT
            for line in fp:
                if "LSORBIT" in line:
                    words = line.split()
                    return words[2] == 'T'
        
        # Error handling: LSORBIT not found
        raise Exception('LSORBIT not found')
        
    @Value_if_true
    def is_relaxed(self):
        # Open up the OUTCAR
        with open(os.path.join(self._directory, 'OUTCAR')) as fp:
        
            #  Look for NSW
            for line in fp:
                if "NSW" in line:
                    words = line.split()
                    return int(words[2]) != 0
                
        # Error handling: NSW not found
        raise Exception('NSW not found')
        
    def get_xc_functional(self):
        # Open up the OUTCAR
        with open(os.path.join(self._directory, 'OUTCAR')) as fp:
        
            # Look for TITEL
            for line in fp:
                if "TITEL" in line:
                    words = line.split()
                    return Value(scalars=[Scalar(value=words[2])])
                    break
            
    def get_pp_name(self):
        # Open up the OUTCAR
        with open(os.path.join(self._directory, 'OUTCAR')) as fp:
        
            #initialize empty list to store pseudopotentials
            pp = []
            # Look for TITEL
            for line in fp:
                if "TITEL" in line:
                    words = line.split()
                    pp.append(words[3])
            return Value(vectors=[[Scalar(value=x) for x in pp]])
                
        # Error handling: TITEL not found
        raise Exception('TITEL not found')
        
    def get_KPPRA(self):
        # Open up the OUTCAR
        with open(os.path.join(self._directory, 'OUTCAR')) as fp:
            #store the number of atoms and number of irreducible K-points
            for line in fp:
                if "NIONS" in line:
                    words = line.split()
                    NI = int(words[11])
                elif "NKPTS" in line:
                    words = line.split()
                    NIRK = float(words[3])
            #check if the number of k-points was reduced by VASP if so, sum all the k-points weight
            if "irreducible" in open(os.path.join(self._directory, 'OUTCAR')).read():
                fp.seek(0)
                for line in fp:
                    #sum all the k-points weight
                    if "Coordinates               Weight" in line:
                        NK=0; counter = 0
                        for line in fp:
                            if counter == NIRK:
                                break
                            NK += float(line.split()[3])
                            counter += 1
                return Value(scalars=[Scalar(value=NI*NK)])
            #if k-points were not reduced KPPRA equals the number of atoms * number of irreducible k-points
            else:
                return Value(scalars=[Scalar(value=NI*NIRK)])

                
        # Error handling: NKPTS or NIONS not found
        raise Exception('NIONS, irredicuble or Coordinates not found')

    def _is_converged(self):
        return self._call_ase(Vasp().read_convergence)

    def get_total_energy(self):
        return Property(scalars=[Scalar(value=self._call_ase(Vasp().read_energy)[0])], units='eV')

    def get_version_number(self):
        # Open up the OUTCAR
        with open(os.path.join(self._directory, 'OUTCAR')) as fp:
        
            #look for vasp
            for line in fp:
                if "vasp" in line:
                    words = line.split()
                    return (words[0].strip('vasp.'))
                    break
        
        # Error handling: vasp not found
        raise Exception('vasp not found')
        
    def get_U_settings(self):
        #Open up the OUTCAR
        with open(os.path.join(self._directory, 'OUTCAR')) as fp:
            #Check if U is used
            if "LDAU" in open(os.path.join(self._directory, 'OUTCAR')).read():
                U_param = {}
                atoms = []
                #get the list of pseupotential used
                for line in fp:
                    if "TITEL" in line:
                        atoms.append(line.split()[3])
                    #Get the U type used
                    if "LDAUTYPE" in line:
                            U_param['Type'] = int(line.split()[-1])
                atoms.reverse()
                fp.seek(0)
                #Get the L value
                U_param['Values'] = {}
                for line in fp:
                    for atom, i in zip(atoms, range(len(atoms))):
                        if "LDAUL" in line:
                                U_param['Values'][atom] = {'L': int(line.split()[-1-i])}
                fp.seek(0)
                #Get the U value            
                for line in fp:
                    for atom, i in zip(atoms, range(len(atoms))):
                        if "LDAUU" in line:
                                U_param['Values'][atom]['U'] = float(line.split()[-1-i])
                fp.seek(0)
                #Get the J value
                for line in fp:
                    for atom, i in zip(atoms, range(len(atoms))):
                        if "LDAUJ" in line:
                                U_param['Values'][atom]['J'] = float(line.split()[-1-i])
                return Value(**U_param)
            #if U is not used, return None
            else:
                return None
            
    def get_vdW_settings(self):
        #define the name of the vdW methods in function of their keyword
        vdW_dict = {'BO':'optPBE-vdW', 'MK':'optB88-vdW', 'ML':'optB86b-vdW','RE':'vdW-DF','OR':'Klimes-Bowler-Michaelides'}
        #Open up the OUTCAR
        with open(os.path.join(self._directory, 'OUTCAR')) as fp:
            #Check if vdW is used
            if "LUSE_VDW" in open(os.path.join(self._directory, 'OUTCAR')).read():
                #if vdW is used, get its keyword             
                for line in fp:
                    if "GGA     =" in line:
                        words = line.split()
                        return Value(scalars=[Scalar(value=vdW_dict[words[2]])])
            #if vdW is not used, return None
            else:
                return None
            
    def get_pressure(self):
        #define pressure dictionnary because since when is kB = kbar? Come on VASP people
        pressure_dict = {'kB':'kbar'}
        #Check if ISIF = 0 is used
        if "ISIF   =      0" in open(os.path.join(self._directory, 'OUTCAR')).read():
            #if ISIF = 0 is used, print this crap
            return None
        #if ISIF is not 0 then extract pressure and units
        else:
            #scan file in reverse to have the final pressure
            for line in reversed(open(os.path.join(self._directory, 'OUTCAR')).readlines()):
                if "external pressure" in line:
                    words = line.split()
                    return Property(scalars=[Scalar(value=float(words[3]))], units=pressure_dict[words[4]])
                    break
    
    def get_stresses(self):
        #Check if ISIF = 0 is used
        if "ISIF   =      0" in open(os.path.join(self._directory, 'OUTCAR')).read():
            return None
        #Check if ISIF = 1 is used
        elif "ISIF   =      1" in open(os.path.join(self._directory, 'OUTCAR')).read():
            return None
        else:
            #scan file in reverse to have the final pressure
            for line in open(os.path.join(self._directory, 'OUTCAR')).readlines():
                if "in kB" in line:
                    words = line.split()
                    XX = float(words[2]); YY = float(words[3]); ZZ = float(words[4]); XY= float(words[5]); YZ = float(words[6]); ZX = float(words[7])
            matrix = [[XX,XY,ZX],[XY,YY,YZ],[ZX,YZ,ZZ]]
            wrapped = [[Scalar(value=x) for x in y] for y in matrix]
            return Property(matrices=[wrapped], units='kbar')
            
         # Error handling: "in kB" not found
        raise Exception('in kB not found')

    def get_forces(self):
        self.atoms = read_vasp_out(os.path.join(self._directory, 'OUTCAR'))
        forces_raw = self.atoms.get_calculator().results['forces'].tolist()
        forces_wrapped = [[Scalar(value=x) for x in y] for y in forces_raw]
        positions_raw = self.atoms.positions.tolist()
        positions_wrapped = [[Scalar(value=x) for x in y] for y in positions_raw]
        return Property(
            vectors=forces_wrapped,
            conditions=Value(name="positions", vectors=positions_wrapped)
        )

    @staticmethod
    def _get_bandgap_from_bands(energies, nelec):
        """Compute difference in conduction band min and valence band max"""
        nelec = int(nelec)
        valence = [x[nelec-1] for x in energies]
        conduction = [x[nelec] for x in energies]
        return max(min(conduction) - max(valence), 0.0)

    @staticmethod
    def _get_bandgap_eigenval(eigenval_fname, outcar_fname):
        """Get the bandgap from the EIGENVAL file"""
        with open(outcar_fname, "r") as f:
            parser = OutcarParser()
            nelec = next(iter(filter(lambda x: "number of electrons" in x, parser.parse(f.readlines()))))["number of electrons"]
        with open(eigenval_fname, "r") as f:
            eigenval_info = list(EigenvalParser().parse(f.readlines()))
        # spin_polarized = (2 == len(next(filter(lambda x: "kpoint" in x, eigenval_info))["occupancies"][0]))
        # if spin_polarized:
        all_energies = [zip(*x["energies"]) for x in eigenval_info if "energies" in x]
        spin_energies = zip(*all_energies)
        gaps = [VaspParser._get_bandgap_from_bands(x, nelec/2.0) for x in spin_energies]
        return min(gaps)

    @staticmethod
    def _get_bandgap_doscar(filename):
        """Get the bandgap from the DOSCAR file"""
        with open(filename) as fp:
            for i in range(6):
                l = fp.readline()
            efermi = float(l.split()[3])
            step1 = fp.readline().split()[0]
            step2 = fp.readline().split()[0]
            step_size = float(step2)-float(step1)
            not_found = True
            while not_found:
                l = fp.readline().split()
                e = float(l.pop(0))
                dens = 0.0
                for i in range(int(len(l)/2)):
                    dens += float(l[i])
                if e < efermi and dens > 1e-3:
                    bot = e
                elif e > efermi and dens > 1e-3:
                    top = e
                    not_found = False
            if top - bot < step_size*2:
                bandgap = 0.0
            else:
                bandgap = float(top - bot)

        return bandgap

    def get_band_gap(self):
        """Get the bandgap, either from the EIGENVAL or DOSCAR files"""
        doscar_path = os.path.join(self._directory, 'DOSCAR')
        outcar_path = os.path.join(self._directory, 'OUTCAR')
        eigenval_path = os.path.join(self._directory, 'EIGENVAL')

        if os.path.isfile(outcar_path) and os.path.isfile(eigenval_path):
            bandgap = VaspParser._get_bandgap_eigenval(eigenval_path, outcar_path)
        elif os.path.isfile(doscar_path):
            bandgap = VaspParser._get_bandgap_doscar(doscar_path)
        else:
            return None
        return Property(scalars=[Scalar(value=round(bandgap, 3))], units='eV')
                
    def get_dos(self):
        file_path = os.path.join(self._directory, 'DOSCAR')
        if not os.path.isfile(file_path):
            return None
        #open DOSCAR
        with open(os.path.join(self._directory, 'DOSCAR')) as fp:
            for i in range(6):
                l = fp.readline()
            n_step = int(l.split()[2])
            energy = []; dos = []            
            for i in range(n_step):
                l = fp.readline().split()
                e = float(l.pop(0))
                energy.append(Scalar(value=e))
                dens = 0
                for j in range(int(len(l)/2)):
                    dens += float(l[j])
                dos.append(Scalar(value=dens))

            # Convert to property
            return Property(scalars=dos, units='number of states per unit cell',
                            conditions=Value(name='energy', scalars=energy, units='eV'))

    def get_total_magnetization(self):
        file_path = os.path.join(self._directory, "OUTCAR")
        if not os.path.isfile(file_path):
            return None
        parser = OutcarParser()
        with open(file_path, "r") as fp:
            matches = list(filter(lambda x: "total magnetization" in x, parser.parse(fp.readlines())))
        if len(matches) == 0:
            return None
        total_magnetization = matches[-1]["total magnetization"]
        return Property(scalars=[Scalar(value=total_magnetization)], units="Bohr")
