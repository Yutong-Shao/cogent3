

import os
from cogent3.util.unit_test import TestCase, main
from cogent3.db.ensembl.host import HostAccount, get_ensembl_account
from cogent3.db.ensembl.compara import Compara

__author__ = "Gavin Huttley, Hua Ying"
__copyright__ = "Copyright 2007-2012, The Cogent Project"
__credits__ = ["Gavin Huttley", "hua Ying"]
__license__ = "GPL"
__version__ = "1.5.3-dev"
__maintainer__ = "Gavin Huttley"
__email__ = "Gavin.Huttley@anu.edu.au"
__status__ = "alpha"

Release = 81

if 'ENSEMBL_ACCOUNT' in os.environ:
    args = os.environ['ENSEMBL_ACCOUNT'].split()
    host, username, password = args[0:3]
    kwargs = {}
    if len(args) > 3:
        kwargs['port'] = int(args[3])
    account = HostAccount(host, username, password, **kwargs)
else:
    account = get_ensembl_account(release=Release)

def calc_slope(x1, y1, x2, y2):
    """computes the slope from two coordinate sets, assigning a delta of 1
    when values are identical"""
    delta_y = y2 - y1
    delta_x = x2 - x1
    delta_y = [delta_y, 1][delta_y == 0]
    delta_x = [delta_x, 1][delta_x == 0]
    return delta_y / delta_x

class ComparaTestBase(TestCase):
    comp = Compara(['human', 'mouse', 'rat', 'platypus'], Release=Release,
                   account=account)

class TestCompara(ComparaTestBase):
    def test_query_genome(self):
        """compara should attach valid genome attributes by common name"""
        brca2 = self.comp.Mouse.getGeneByStableId("ENSMUSG00000041147")
        self.assertEqual(brca2.Symbol.lower(), 'brca2')

    def test_get_related_genes(self):
        """should correctly return the related gene regions from each genome"""
        brca2 = self.comp.Mouse.getGeneByStableId("ENSMUSG00000041147")
        Orthologs = self.comp.getRelatedGenes(gene_region=brca2,
                                              Relationship="ortholog_one2one")
        self.assertEqual("ortholog_one2one", Orthologs.Relationships[0])

    def test_get_related_genes2(self):
        """should handle case where gene is absent from one of the genomes"""
        clec2d = self.comp.Mouse.getGeneByStableId(
            StableId='ENSMUSG00000030157')
        orthologs = self.comp.getRelatedGenes(gene_region=clec2d,
                                              Relationship='ortholog_one2many')
        self.assertTrue(len(orthologs.Members) < 4)

    def test_get_collection(self):
        brca2 = self.comp.Human.getGeneByStableId(StableId="ENSG00000139618")
        Orthologs = self.comp.getRelatedGenes(gene_region=brca2,
                                              Relationship="ortholog_one2one")
        collection = Orthologs.getSeqCollection()
        self.assertTrue(len(collection.Seqs[0]) > 1000)

    def test_getting_alignment(self):
        mid = "ENSMUSG00000041147"
        brca2 = self.comp.Mouse.getGeneByStableId(StableId=mid)
        result = list(self.comp.getSyntenicRegions(region=brca2,
                                                   align_method='PECAN', align_clade='vertebrates'))[0]
        aln = result.getAlignment(feature_types='gene')
        # to improve test robustness across Ensembl releases, where alignment
        # coordinates change due to inclusion of new species, we search for
        # the mouse subseq and use the resulting coords to ensure we get the
        # same match as that from the Ensembl website
        mouse_name = [n for n in aln.Names if "Mus musculus" in n][0]
        start = aln.todict()[mouse_name].find('AAGTCAAACTCTACCACTGG')
        sub_aln = aln[start: start + 20]
        seqs = list(sub_aln.todict().values())
        expect = set(['AGGGCTGACTCTGCCGCTGT',  # human
                      'AAGTCAAACTCTACCACTGG',  # mouse
                      'AAGTCAAACTCTACCACTAG',  # rat
                      'AAATGTGACTCTACCAGCCG'  # platypus
                      ])
        self.assertEqual(set(seqs), expect)
        self.assertTrue(len(aln) > 1000)

    def test_generate_method_clade_data(self):
        """should correctly determine the align_method align_clade options for
        a group of species"""
        # we should correctly infer the method_species_links, which is a
        # cogent3.util.Table instance
        self.assertTrue(self.comp.method_species_links.Shape > (0, 0))

    def test_no_method_clade_data(self):
        """generate a Table with no rows if no alignment data"""
        compara = Compara(['S.cerevisiae'], Release=Release, account=account)
        self.assertEqual(compara.method_species_links.Shape[0], 0)

    def test_get_syntenic_returns_nothing(self):
        """should correctly return None for a SyntenicRegion with golden-path
        assembly gap"""
        Start = 100000
        End = Start + 100000
        related = list(self.comp.getSyntenicRegions(Species='mouse',
                                                    CoordName='1', Start=Start, End=End,
                                                    align_method='PECAN', align_clade='vertebrates'))
        self.assertEqual(related, [])

    def test_get_species_set(self):
        """should return the correct set of species"""
        expect = set(['Homo sapiens', 'Ornithorhynchus anatinus',
                      'Mus musculus', 'Rattus norvegicus'])
        brca1 = self.comp.Human.getGeneByStableId(StableId="ENSG00000012048")
        Orthologs = self.comp.getRelatedGenes(gene_region=brca1,
                                              Relationship="ortholog_one2one")
        self.assertEqual(Orthologs.getSpeciesSet(), expect)

    def test_pool_connection(self):
        """excercising ability to specify pool connection"""
        dog = Compara(['chimp', 'dog'], Release=Release, account=account,
                      pool_recycle=1000)



class TestSyntenicRegions(TestCase):
    comp = Compara(['human', 'chimp', 'macaque'], account=account,
                   Release=Release)

    def test_correct_alignments(self):
        """should return the correct alignments"""
        # following cases have a mixture of strand between ref seq and others
        coords_expected = [
            [{'CoordName': 4, 'End': 78207, 'Species': 'human', 'Start': 78107, 'Strand': -1},
             {'Homo sapiens:chromosome:4:77999-78099:-1':
              'ATGTAAATCAAAACCAAAGTCTGCATTTATTTGCGGAAAGAGATGCTACATGTTCAAAGATAAATATGGAACATTTTTTAAAAGCATTCATGACTTAGAA',
              'Macaca mulatta:chromosome:1:3891064-3891163:1':
              'ATGTCAATCAAAACCAAAGTCTGTATTTATTTGCAGAAAGAGATACTGCATGTTCAAAGATAAATATGGAAC-TTTTTAAAAAGCATTAATGACTTATAC',
              'Pan troglodytes:chromosome:4:102056-102156:-1':
              'ATGTAAATCAAAACCAAAGTCTGCATTTATTTGCGGAAAGAGATGCTACATGTTCAAAGATAAATATGGAACATTTTTAAAAAGCATTCATGACTTAGAA'}],
            [{'CoordName': 18, 'End': 213739, 'Species': 'human', 'Start': 213639, 'Strand': -1},
                {'Homo sapiens:chromosome:18:213639-213739:-1':
                 'ATAAGCATTTCCCTTTAGGGCTCTAAGATGAGGTCATCATCGTTTTTAATCCTGAAGAAGGGCTACTGAGTGAGTGCAGATTATTCGGTAAACACT----CTTA',
                 'Macaca mulatta:chromosome:18:13858303-13858397:1':
                 '------GTTTCCCTTTAGGGCTCTAAGATGAGGTCATCATTGTTTTTAATCCTGAAGAAGGGCTACTGA----GTGCAGATTATTCTGTAAATGTGCTTACTTG',
                 'Pan troglodytes:chromosome:18:16601082-16601182:1':
                 'ATAAGCATTTCCCTTTAGGGCTCTAAGATGAGGTCATCATCGTTTTTAATCCTGAAGAAGGGCTACTGA----GTGCAGATTATTCTGTAAACACTCACTCTTA'}],
            [{'CoordName': 5, 'End': 204859, 'Species': 'human', 'Start': 204759, 'Strand': 1},
                {'Homo sapiens:chromosome:5:204874-204974:1':
                 'AACACTTGGTATTT----CCCCTTTATGGAGTGAGAGAGATCTTTAAAATATAAACCCTTGATAATATAATATTACTACTTCCTATTA---CCTGTTATGCAGTTCT',
                 'Macaca mulatta:chromosome:6:1297736-1297840:-1':
                 'AACTCTTGGTGTTTCCTTCCCCTTTATGG---GAGAGAGATCTTTAAAATAAAAAACCTTGATAATATAATATTACTACTTTCTATTATCATCTGTTATGCAGTTCT',
                 'Pan troglodytes:chromosome:5:335911-336011:1':
                 'AACACTTGGTAGTT----CCCCTTTATGGAGTGAGAGAGATCTTTAAAATATAAACCCTTGATAATATAATATTACTACTTTCTATTA---CCTGTTATGCAGTTCT'}],
            [{'CoordName': 18, 'End': 203270, 'Species': 'human', 'Start': 203170, 'Strand': -1},
                {'Homo sapiens:chromosome:18:203170-203270:-1':
                 'GGAATAATGAAAGCAATTGTGAGTTAGCAATTACCTTCAAAGAATTACATTTCTTATACAAAGTAAAGTTCATTACTAACCTTAAGAACTTTGGCATTCA',
                 'Pan troglodytes:chromosome:18:16611584-16611684:1':
                 'GGAATAATGAAAGCAATTGTAAGTTAGCAATTACCTTCAAAGAATTACATTTCTTATACAAAGTAAAGTTCATTACTAACCTTAAGAACTTTGGCATTCA'}],
            [{'CoordName': 2, 'End': 46445, 'Species': 'human', 'Start': 46345, 'Strand': -1},
                {'Homo sapiens:chromosome:2:46345-46445:-1':
                 'CTACCACTCGAGCGCGTCTCCGCTGGACCCGGAACCCCGGTCGGTCCATTCCCCGCGAAGATGCGCGCCCTGGCGGCCCTGAGCGCGCCCCCGAACGAGC',
                 'Macaca mulatta:chromosome:13:43921-44021:-1':
                 'CTGCCACTCCAGCGCGTCTCCGCTGCACCCGGAGCGCCGGCCGGTCCATTCCCCGCGAGGATGCGCGCCCTGGCGGCCCTGAACACGTCGGCGAGAGAGC',
                 'Pan troglodytes:chromosome:2a:36792-36892:-1':
                 'CTACCACTCGAGCGCGTCTCCGCTGGACCCGGAACCCCAGTCGGTCCATTCCCCGCGAAGATGCGCGCCCTGGCGGCCCTGAACGCGCCCCCGAACGAGC'}],
            [{'CoordName': 18, 'End': 268049, 'Species': 'human', 'Start': 267949, 'Strand': -1},
                {'Homo sapiens:chromosome:18:267949-268049:-1':
                 'GCGCAGTGGCGGGCACGCGCAGCCGAGAAGATGTCTCCGACGCCGCCGCTCTTCAGTTTGCCCGAAGCGCGGACGCGGTTTACGGTGAGCTGTAGAGGGG',
                 'Macaca mulatta:chromosome:18:13805604-13805703:1':
                 'GCGCAG-GGCGGGCACGCGCAGCCGAGAAGATGTCTCCGACGCCGCCGCTCTTCAGTTTGCCCGAAGCGCGGACGCGGTTTACGGTGAGCTGTAGGCGGG',
                 'Pan troglodytes:chromosome:18:16546800-16546900:1':
                 'GCGCAGTGGCGGGCACGCGCAGCCGAGAAGATGTCTCCGACGCCGCCGCTCTTCAGTTTGCCCGAAGCGCGGACGCGGTTTACGGTGAGCTGTAGCGGGG'}],
            [{'CoordName': 16, 'End': 57443, 'Species': 'human', 'Start': 57343, 'Strand': -1},
                {'Homo sapiens:chromosome:16:107343-107443:-1':
                 'AAGAAGCAAACAGGTTTATTTTATACAGTGGGCCAGGCCGTGGGTCTGCCATGTGACTAGGGCATTTGGACCTAGGGAGAGGTCAGTCTCAGGCCAAGTA',
                 'Pan troglodytes:chromosome:16:48943-49032:-1':
                 'AAGAAGCAAACAGGTTTATTTTATACACTGGGCCAGGCCGTGGGTCTGCCATGTGACTAGGGAATTTGGACC-----------CAGTCTCAGGCCAAGTA'}]
        ]
        # print self.comp.method_species_links
        for coord, expect in coords_expected[1:]:
            syntenic = list(
                self.comp.getSyntenicRegions(method_clade_id=742, **coord))[0]
            # check the slope computed from the expected and returned
            # coordinates is ~ 1
            got_names = dict([(n.split(':')[0], n.split(':')) for n in syntenic.getAlignment().Names])
            exp_names = dict([(n.split(':')[0], n.split(':')) for n in list(expect.keys())])
            for species in exp_names:
                exp_chrom = exp_names[species][2]
                got_chrom = got_names[species][2]
                self.assertEqual(exp_chrom.lower(), got_chrom.lower())
                exp_start, exp_end = list(map(int, exp_names[species][3].split('-')))
                got_start, got_end = list(map(int, got_names[species][3].split('-')))
                slope = calc_slope(exp_start, exp_end, got_start, got_end)
                self.assertFloatEqual(abs(slope), 1.0, eps=1e-3)


    def test_failing_region(self):
        """should correctly handle queries where multiple Ensembl have
        genome block associations for multiple coord systems"""
        gene = self.comp.Human.getGeneByStableId(StableId='ENSG00000188554')
        # this should simply not raise any exceptions
        syntenic_regions = list(self.comp.getSyntenicRegions(region=gene,
                                                             align_method='PECAN',
                                                             align_clade='vertebrates'))



if __name__ == "__main__":
    main()
