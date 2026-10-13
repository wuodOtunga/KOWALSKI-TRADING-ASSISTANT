#MODULE TO HANDLE VALIDATION AND EXCEPTION INSTANCES.

#RESEARCH ON THESE SQLITE3 ERRORS BETTER FROM SQLITE3 MODULE DOCS.
######
#Using e.orig to pin down the SQLite error
#SQLAlchemy wraps the drivers exception. e is sqlalchemy.exc.IntegrityError,
#and e.orig is the original sqlite3.IntegrityError.
#On Python 3.11+ that object carries two attributes the code ignores today:

#sqlite_errorname, e.g. "SQLITE_CONSTRAINT_UNIQUE"
#sqlite_errorcode, the numeric version

#The constraint subtypes are _FOREIGNKEY, _UNIQUE, _PRIMARYKEY, _CHECK and _NOTNULL.
#The message text adds detail the code doesnt:

#UNIQUE constraint failed: charts.filename gives you table and column.
#CHECK constraint failed: ck_trades_asset gives you the constraint name,
# which is why naming your constraints pays off.
#FOREIGN KEY constraint failed gives you nothing more,
#so FK violations are best prevented by pre-checks
#####

#SQLITE3 EXCEPTION CLASSES HIERARCHY
#Exception as the base class.
#Under the Exception base class, we have two child classes: Error and Warning.
#Under the Error class, we have two child classes: DatabaseError and InterfaceError.
#Under DatabaseError class, we have 6 child classes all inheriting from their parent, DatabaseError.
#DataError, IntegrityError, InternalError, NotSupportedError, OperationalError, ProgrammingError.

# --------------------------------------------------------------------------
#   PARENT BASE CLASS EXCEPTIONS FOR APP ERRORS
# --------------------------------------------------------------------------

class KowalskiError(Exception):
    """BASE CLASS FOR ALL APP EXCEPTIONS"""

# --------------------------------------------------------------------------
#   CHILD CLASS EXCEPTIONS INHERITING FROM PARENT BASE CLASS
# --------------------------------------------------------------------------
class JournalingError(KowalskiError):
    """EXCEPTION CLASS FOR JOURNAL WORKFLOW ERRORS"""

class RepositoryError(KowalskiError):
    """EXCEPTION CLASS FOR DATABASE QUERY EXCEPTIONS"""

class InternalDomainError(KowalskiError):
    """EXCEPTION CLASS FOR INTERNAL ERRORS LIKE RESOURCE RECORDING ERRORS"""

# --------------------------------------------------------------------------
#   JournalingError CLASS CHILD EXCEPTIONS FOR JOURNAL WORKFLOW EXCEPTIONS
# --------------------------------------------------------------------------
class TradeValidationError(JournalingError):
    """EXCEPTION CLASS FOR ALL DOMAIN VALIDATION ERRORS"""

class GradingError(JournalingError):
    """EXCEPTION CLASS FOR HANDLING GRADING ERRORS."""

class ConflictError(JournalingError):
    """EXCEPTION CLASS FOR JOURNAL WORKFLOW STATE CONFLICT ERRORS"""

class TradeAlreadyGradedError(ConflictError):
    """EXCEPTION CLASS FOR TRYING TO GRADE A GRADED TRADE"""

class ParametersConflictError(ConflictError):
    """EXCEPTION CLASS FOR JOINT PRIMARY KEY VIOLATION IN PARAMETERS TABLE"""

# --------------------------------------------------------------------------
#   InternalDomainError CLASS CHILD EXCEPTIONS FOR RESOURCE UPLOAD ERRORS
# --------------------------------------------------------------------------

class TradeRecordingError(InternalDomainError):
    """EXCEPTION CLASS FOR TRADE RESOURCE UPLOAD ERRORS."""

class ChartUploadError(InternalDomainError):
    """EXCEPTION CLASS FOR CHARTS RESOURCE UPLOAD ERRORS."""

class NotesRecordingError(InternalDomainError):
    """EXCEPTION CLASS FOR NOTES RESOURCE UPLOAD ERRORS."""

class JournalEntryError(InternalDomainError):
    "EXCEPTION CLASS FOR JOURNAL ENTRY RESOURCE UPLOAD ERRORS."

class AccountCreationError(InternalDomainError):
    """EXCEPTION CLASS FOR ACCOUNTS RESOURCE CREATION ERRORS"""

class ConstraintViolationError(InternalDomainError):
    """EXCEPTION CLASS FOR TABLE/COLUMN CONSTRAINTS VIOLATIONS"""

class ForeignKeyViolationError(ConstraintViolationError):
    """EXCEPTION CLASS FOR FOREIGN KEY CONSTRAINT VIOLATION ERRORS"""

class UniqueViolationError(ConstraintViolationError):
    """EXCEPTION CLASS FOR UNIQUE CONSTRAINT VIOLATION ERRORS"""
    """this contains unique constraints for the UNIQUE column constraint
    and the PRIMARY KEY unique column constraint"""

class CheckViolationError(ConstraintViolationError):
    """EXCEPTION CLASS FOR CHECK CONSTRAINT VIOLATION ERRORS"""
    """Domain enums for trade attributes like asset, direction, result
    overall_trade_grade have CHECK constraints that validates that the input
    values for these attributes are values that are members of the enums. If not
    then a CHECK constraint violation occurs. Other CHECK constraints in the database include
    entry_execution_points in entry_execution table must be integer values between 1 and 5
    The entry_execution grade must be a value between A+ and F. These same CHECK constraints
    apply for the trade_management table. Accounts table has a CHECK constraint that asserts that
    account_type column must fall between three values of
    'FUNDED CHALLENGE', 'FUNDED LIVE', 'PERSONAL LIVE'. Input values that don't match violates
    the CHECK constraint causing a CheckViolationError."""

class NotNullViolationError(ConstraintViolationError):
    """EXCEPTION CLASS FOR NOT NULL CONSTRAINT VIOLATION ERRORS."""
    """this fires when the column value is required but the input was a None/NULL value"""

# --------------------------------------------------------------------------
#   RepositoryError CLASS CHILD EXCEPTIONS FOR RESOURCE QUERY ERRORS
# --------------------------------------------------------------------------

class NotFoundError(RepositoryError):
    """EXCEPTION CLASS FOR A RESOURCE NOT FOUND IN THE DATABASE"""

class TradeNotFoundError(NotFoundError):
    """EXCEPTION CLASS FOR A TRADE NOT FOUND IN THE DATABASE"""

class NotesNotFoundError(NotFoundError):
    """EXCEPTION CLASS FOR NOTES NOT FOUND IN THE DATABASE"""

class InvalidIdentifierError(NotFoundError):
    """EXCEPTION CLASS FOR RESOURCES NOT FOUND DUE TO INVALID IDENTIFIERS"""
    """IDENTIFIERS INCLUDE ACCOUNTID, MANAGEMENTID, MODELID, ENTRY_EXECUTIONID"""

class ChartsNotFoundError(NotFoundError):
    """EXCEPTION CLASS FOR CHARTS NOT FOUND IN THE DATABASE"""
