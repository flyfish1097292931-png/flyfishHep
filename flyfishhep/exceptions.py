"""Dependency-free shared contract exception."""


class ContractError(ValueError):
    """Invalid contract, authorization or evidence; never a physics verdict."""
