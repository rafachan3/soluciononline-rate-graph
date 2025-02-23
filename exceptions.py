class QuoterError(Exception):
    """Base exception class for Quoter errors"""
    pass

class PlanSelectionError(QuoterError):
    """Raised when there's an error selecting a plan"""
    pass

class DataCollectionError(QuoterError):
    """Raised when there's an error collecting plan data"""
    pass

class NavigationError(QuoterError):
    """Raised when there's an error navigating pages"""
    pass

class ElementInteractionError(QuoterError):
    """Raised when there's an error interacting with page elements"""
    pass