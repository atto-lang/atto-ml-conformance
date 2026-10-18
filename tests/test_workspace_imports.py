"""Synthetic self-contained import graph: no private Oreslang files or compiler."""
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from check_workspace_imports import validate_workspace_imports


class WorkspaceImportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for name in ("oreslang-tensor", "oreslang-autograd", "oreslang-ml"):
            (self.root / name / "src").mkdir(parents=True)
        self.tensor = self.root / "oreslang-tensor/src/tensor.ores"
        self.autograd = self.root / "oreslang-autograd/src/tape.ores"
        self.ml = self.root / "oreslang-ml/src/model.ores"
        self.tensor.write_text("define pub class TensorF64 as\nend\npub fnc checked_numel(): int { return 1; }\n")
        self.autograd.write_text("import class TensorF64 from '../../oreslang-tensor/src/tensor';\n"
                                 "import fnc checked_numel from '../../oreslang-tensor/src/tensor';\n"
                                 "define pub class TapeF64 as\nend\n")
        self.ml.write_text("import class TapeF64 from '../../oreslang-autograd/src/tape';\n"
                           'import module Assert from "std/assert";\n')

    def test_positive_exact_three_repo_graph(self):
        r = validate_workspace_imports(self.root)
        self.assertEqual(r["source_files"], 3)
        self.assertEqual(r["imports_verified"], 4)
        self.assertEqual(len(r["cross_repository_edges"]), 2)
        self.assertFalse(r["guest_executed"])

    def test_missing_provider(self):
        self.tensor.unlink()
        with self.assertRaisesRegex(ValueError, "source count"):
            validate_workspace_imports(self.root)

    def test_missing_public_symbol(self):
        self.tensor.write_text("define pub class TensorF64 as\nend\n")
        with self.assertRaisesRegex(ValueError, "publicly declared"):
            validate_workspace_imports(self.root)

    def test_undeclared_external_dependency(self):
        self.ml.write_text("import class Unknown from '../../new-repo/src/u';\n")
        with self.assertRaisesRegex(ValueError, "missing Oreslang import target|escapes pinned workspace"):
            validate_workspace_imports(self.root)

    def test_undeclared_reverse_cross_edge(self):
        self.tensor.write_text(self.tensor.read_text()+"import class TapeF64 from '../../oreslang-autograd/src/tape';\n")
        with self.assertRaisesRegex(ValueError, "unapproved cross-repository"):
            validate_workspace_imports(self.root)

    def test_missing_essential_autograd_dependency(self):
        self.ml.write_text("pub fnc model(): int { return 1; }\n")
        with self.assertRaisesRegex(ValueError, "closure incomplete"):
            validate_workspace_imports(self.root)

    def test_symlink_import_denied(self):
        self.tensor.rename(self.tensor.with_suffix(".tmp"))
        self.tensor.symlink_to(self.tensor.with_suffix(".tmp"))
        with self.assertRaisesRegex(ValueError, "symlink"):
            validate_workspace_imports(self.root)

    def test_unknown_standard_import_denied(self):
        self.ml.write_text(self.ml.read_text()+"import module OS from 'std/os';\n")
        with self.assertRaisesRegex(ValueError, "unapproved external"):
            validate_workspace_imports(self.root)

    def test_duplicate_import_denied(self):
        self.ml.write_text(self.ml.read_text()+"import class TapeF64 from '../../oreslang-autograd/src/tape';\n")
        with self.assertRaisesRegex(ValueError, "duplicate imported"):
            validate_workspace_imports(self.root)

    def test_malformed_import_denied(self):
        self.ml.write_text(self.ml.read_text()+"import fnc x from 'not-ended'\n")
        with self.assertRaisesRegex(ValueError, "unrecognized Oreslang import syntax"):
            validate_workspace_imports(self.root)

    def test_null_byte_denied(self):
        self.tensor.write_bytes(b"define pub class TensorF64 as\x00end")
        with self.assertRaisesRegex(ValueError, "NUL"):
            validate_workspace_imports(self.root)


if __name__ == "__main__":
    unittest.main()
