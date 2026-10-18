use gix::index::entry::Mode;
use pyo3::exceptions::PyRuntimeError;
use pyo3::prelude::*;
use std::path::{Path, PathBuf};

#[pyclass(unsendable)]
struct IgnoreMatcher {
    repo: gix::Repository,
    stack: gix::worktree::Stack,
}

#[pymethods]
impl IgnoreMatcher {
    #[new]
    fn new(directory: PathBuf) -> PyResult<Self> {
        let repo = gix::discover(&directory).map_err(|e| PyRuntimeError::new_err(e.to_string()))?;

        let index = repo
            .index_or_empty()
            .map_err(|e| PyRuntimeError::new_err(e.to_string()))?;

        let stack = repo
            .excludes(
                &index,
                None,
                gix::worktree::stack::state::ignore::Source::WorktreeThenIdMappingIfNotSkipped,
            )
            .map_err(|e| PyRuntimeError::new_err(e.to_string()))?
            .detach();

        Ok(Self { repo, stack })
    }

    #[getter]
    fn repo_root(&self) -> Option<PathBuf> {
        self.repo.workdir().map(Path::to_path_buf)
    }

    fn ignored_many(&mut self, paths: Vec<(String, bool)>) -> PyResult<Vec<bool>> {
        let mut results = vec![false; paths.len()];
        let mut order: Vec<usize> = (0..paths.len()).collect();

        // Visit paths in lexical order to improve stack-cache reuse.
        order.sort_unstable_by(|&a, &b| paths[a].0.cmp(&paths[b].0));

        for index in order {
            let (path, is_dir) = &paths[index];
            let mode = if *is_dir { Mode::DIR } else { Mode::FILE };

            let platform = self
                .stack
                .at_path(path.as_str(), Some(mode), &self.repo.objects)
                .map_err(|e| PyRuntimeError::new_err(e.to_string()))?;

            results[index] = platform.is_excluded();
        }

        Ok(results)
    }
}

#[pymodule]
fn _native(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<IgnoreMatcher>()?;
    Ok(())
}
