use pyo3::prelude::*;
use pyo3::Py;

mod checker;
mod config;
mod discovery;
mod noqa;
mod rule;
mod rules;
mod violation;

#[pyfunction]
#[pyo3(signature = (paths, python_rules, config_path=None))]
fn check_files(
    py: Python<'_>,
    paths: Vec<String>,
    python_rules: Vec<Py<PyAny>>,
    config_path: Option<String>,
) -> PyResult<Vec<violation::Violation>> {
    checker::run_check(paths, &python_rules, config_path, py)
}

#[pymodule]
fn _internal(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<violation::Violation>()?;
    m.add_function(wrap_pyfunction!(check_files, m)?)?;
    Ok(())
}
