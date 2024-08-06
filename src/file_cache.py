from dataclasses import dataclass
from typing import Any, TypeVar, Callable, cast
import functools
import os
import pickle
import inspect
from hashlib import sha256
from pathlib import Path
import time
from collections import defaultdict
# import atexit
# from tempfile import TemporaryFile


def calculate_sha(text: str) -> str:
    sha_value = sha256(text.encode()).hexdigest()
    return sha_value


TCallable = TypeVar("TCallable", bound=Callable)

# CACHE_DIRECTORY: str = "temporary_cache_dir"
CACHE_DIRECTORY = Path.cwd() / "temporary_cache_dir"


@dataclass()
class data:
    cache_filename: Path
    cache_data: Any
    delete_afterwards: bool


# pyright: reportAny=false
# pyright: reportUnknownParameterType=false
# pyright: reportMissingParameterType=false
# pyright: reportUnknownArgumentType=false
# pyright: reportUnknownVariableType=false
# pyright: reportMissingTypeArgument=false


cache_data: list[data] = []


def cache(
    prefix_name: str = "",
    extension: str = "pickle",
    persistent_after_termination: bool = False,
    sub_directory: Path | None = None,
    extra_info_in_shahash: str = "",
):
    def file_cache_decorator(annotated_function: TCallable) -> TCallable:
        @functools.wraps(annotated_function)
        def wrapper(*args, **kwargs):
            global cache_data
            function_signature_unique = calculate_sha(
                inspect.getsource(annotated_function)
                + "".join(str(x) for x in args)
                + "".join(f"{x[0]}{x[1]}" for x in kwargs.items())
                + extra_info_in_shahash
            )

            # function_signature_unique2 = calculate_sha(
            #     inspect.getsource(annotated_function)
            #     + "".join(str(x) for x in args)
            #     + "".join(f"{x[0]}{x[1]}" for x in kwargs.items())
            # )

            # assert (
            #     function_signature_unique == function_signature_unique2
            # ), "sha issues!!"

            # print(">FINDING IN CACHE...")
            # cache_filename = f"{CACHE_DIRECTORY}/{prefix_name}cache-{function_signature_unique}.{extension}"
            cache_filename = (
                CACHE_DIRECTORY
                / (sub_directory if sub_directory is not None else Path())
                / f"{prefix_name}cache-{function_signature_unique}.{extension}"
            )

            if not os.path.exists(cache_filename.parent):
                try:
                    os.makedirs(cache_filename.parent)
                except FileExistsError:
                    # actually did get this error, I'm guessing by multithreading
                    print("File already exists")

            if matching_data := [
                x for x in cache_data if x.cache_filename.name == cache_filename.name
            ]:
                return matching_data[0].cache_data

            # if os.path.exists(cache_filename):
            if cache_filename.is_file():
                with cache_filename.open("rb") as f:
                    recieved_value_data = pickle.load(f)
                    # cache_data.append(recieved_value_data)
                    cache_data.append(
                        data(
                            cache_filename,
                            recieved_value_data,
                            delete_afterwards=not persistent_after_termination,
                        )
                    )
                    return recieved_value_data.cache_data

            # if sub_directory is not None:
            #     print(
            #         cache_filename,
            #         inspect.getsource(annotated_function)
            #         + "".join(str(x) for x in args)
            #         + "".join(f"{x[0]}{x[1]}" for x in kwargs.items()),
            #     )
            #     _ = input(">>RENDERING INSTEAD OF CACHE")

            recieved_value = annotated_function(*args, **kwargs)

            cache_data.append(
                recieved_value_data := data(
                    cache_filename, recieved_value, not persistent_after_termination
                )
            )

            cache_filename.parent.mkdir(parents=True, exist_ok=True)
            with cache_filename.open("wb") as f:
                pickle.dump(recieved_value_data, f)
            # with open(str(cache_filename), "wb") as f:
            #     pickle.dump(recieved_value, f)

            print("written to cache")
            # _ = os.system("tree") # (debugging)

            return recieved_value

        return cast(TCallable, wrapper)

    return file_cache_decorator


def cache_cleanup():
    print("cleaning up cache files at the end")
    for file in (x for x in cache_data if x.delete_afterwards):
        try:
            os.remove(file.cache_filename)
        except Exception as e:
            print(f"ERROR REMOVING CACHE FILE: {e}")


# def recording_timer(annotated_function: TCallable) -> TCallable:
#     @functools.wraps(annotated_function)
#     def wrapper(*args, **kwargs):
#         start = time.perf_counter()
#         recieved_value = annotated_function(*args, **kwargs)
#         elapsed = time.perf_counter() - start
#
#         return recieved_value
#
#     return cast(TCallable, wrapper)


# _ = atexit.register(cache_cleanup)

# import hashlib
# import inspect
# import os
# import pickle
#
# from loguru import logger
#
# DISABLE_CACHE = False
#
# MAX_DEPTH = 6
# if DISABLE_CACHE:
#     print("File cache is disabled.")
#
#
# def recursive_hash(value, depth=0, ignore_params=[]):
#     """Hash primitives recursively with maximum depth."""
#     if depth > MAX_DEPTH:
#         return hashlib.md5("max_depth_reached".encode()).hexdigest()
#
#     if isinstance(value, (int, float, str, bool, bytes)):
#         return hashlib.md5(str(value).encode()).hexdigest()
#     elif isinstance(value, (list, tuple)):
#         return hashlib.md5(
#             "".join(
#                 [recursive_hash(item, depth + 1, ignore_params) for item in value]
#             ).encode()
#         ).hexdigest()
#     elif isinstance(value, dict):
#         return hashlib.md5(
#             "".join(
#                 [
#                     recursive_hash(key, depth + 1, ignore_params)
#                     + recursive_hash(val, depth + 1, ignore_params)
#                     for key, val in value.items()
#                     if key not in ignore_params
#                 ]
#             ).encode()
#         ).hexdigest()
#     elif hasattr(value, "__dict__") and value.__class__.__name__ not in ignore_params:
#         return recursive_hash(value.__dict__, depth + 1, ignore_params)
#     else:
#         return hashlib.md5("unknown".encode()).hexdigest()
#
#
# def hash_code(code):
#     return hashlib.md5(code.encode()).hexdigest()
#
#
# def file_cache(ignore_params=[], verbose=False):
#     """Decorator to cache function output based on its inputs, ignoring specified parameters.
#     Ignore parameters are used to avoid caching on non-deterministic inputs, such as timestamps.
#     We can also ignore parameters that are slow to serialize/constant across runs, such as large objects.
#     """
#
#     def decorator(func):
#         if DISABLE_CACHE:
#             if verbose:
#                 print("Cache is disabled for function: " + func.__name__)
#             return func
#         func_source_code_hash = hash_code(inspect.getsource(func))
#
#         def wrapper(*args, **kwargs):
#             cache_dir = "/mnt/caches/file_cache"
#             os.makedirs(cache_dir, exist_ok=True)
#
#             # Convert args to a dictionary based on the function's signature
#             args_names = func.__code__.co_varnames[: func.__code__.co_argcount]
#             args_dict = dict(zip(args_names, args))
#
#             # Remove ignored params
#             kwargs_clone = kwargs.copy()
#             for param in ignore_params:
#                 args_dict.pop(param, None)
#                 kwargs_clone.pop(param, None)
#
#             # Create hash based on argument names, argument values, and function source code
#             arg_hash = (
#                 recursive_hash(args_dict, ignore_params=ignore_params)
#                 + recursive_hash(kwargs_clone, ignore_params=ignore_params)
#                 + func_source_code_hash
#             )
#             cache_file = os.path.join(
#                 cache_dir, f"{func.__module__}_{func.__name__}_{arg_hash}.pickle"
#             )
#
#             try:
#                 # If cache exists, load and return it
#                 if os.path.exists(cache_file):
#                     if verbose:
#                         print("Used cache for function: " + func.__name__)
#                     with open(cache_file, "rb") as f:
#                         return pickle.load(f)
#             except Exception:
#                 logger.info("Unpickling failed")
#
#             # Otherwise, call the function and save its result to the cache
#             result = func(*args, **kwargs)
#             try:
#                 with open(cache_file, "wb") as f:
#                     pickle.dump(result, f)
#             except Exception as e:
#                 logger.info(f"Pickling failed: {e}")
#             return result
#
#         return wrapper
#
#     return decorator
#
#


@dataclass
class timedata:
    total_time: float
    number_of_calls: int


# time_of_functions: defaultdict[str, float] = defaultdict()
time_of_functions: dict[str, timedata] = {}


def store_cumulative_time(annotated_function: TCallable) -> TCallable:
    @functools.wraps(annotated_function)
    def wrapper(*args, **kwargs):
        global time_of_functions

        start_time = time.perf_counter()
        recieved_value = annotated_function(*args, **kwargs)
        elapsed_time = time.perf_counter() - start_time

        # time_of_functions.append(timedata(annotated_function.__name__, elapsed_time))
        try:
            time_of_functions[annotated_function.__name__] = timedata(
                time_of_functions[annotated_function.__name__].total_time
                + elapsed_time,
                time_of_functions[annotated_function.__name__].number_of_calls + 1,
            )
        except KeyError:
            time_of_functions[annotated_function.__name__] = timedata(elapsed_time, 1)

        return recieved_value

    return cast(TCallable, wrapper)


def print_times_of_functions():
    from rich import print

    print(time_of_functions)


if __name__ == "__main__":
    import time

    @cache()
    def get_result(delay: int) -> str:
        time.sleep(delay)
        return str(delay)

    print(get_result(1))
    print(get_result(2))
    print(get_result(3))

    cache_cleanup()
