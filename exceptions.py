class QuoterError(Exception):
    """Base exception class for Quoter errors

    This serves as the parent class for all more specific error types
    in the quoter application, providing a common exception type that
    can be caught to handle any quoter error.
    """
    pass

class PlanSelectionError(QuoterError):
    """Raised when there's an error selecting a plan

    This occurs when the application cannot properly select a plan from
    the dropdown or when an unknown plan type is encountered. Common causes
    include UI changes on the insurance portal or configuration issues.
    """
    pass

class DataCollectionError(QuoterError):
    """Raised when there's an error collecting plan data

    This occurs when the application is unable to retrieve pricing information
    from the results page. This might happen due to unexpected UI changes,
    missing elements, or when the insurance system returns an error state.
    """
    pass

class NavigationError(QuoterError):
    """Raised when there's an error navigating pages

    This occurs when the application cannot successfully move between different
    sections of the insurance portal. Common causes include timeout issues,
    unexpected redirects, or UI changes that break navigation flows.
    """
    pass

class ElementInteractionError(QuoterError):
    """Raised when there's an error interacting with page elements

    This occurs when the application cannot find, click, or extract data from
    specific UI elements. This might happen due to UI changes, element state issues,
    or timing problems with dynamic content loading.
    """
    pass