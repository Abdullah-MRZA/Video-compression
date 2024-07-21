from dataclasses import dataclass
import pathlib
import time
from typing import Any, TypeVar, Callable, cast
import functools
import os
import pickle
import inspect
from hashlib import sha256
import atexit
# from pathlib import Path
# from tempfile import TemporaryFile


def calculate_sha(text: str) -> str:
    sha_value = sha256(text.encode()).hexdigest()
    return sha_value


TCallable = TypeVar("TCallable", bound=Callable)
# _basepath = Path()

cache_directory = "cache_dir"


@dataclass()
class data:
    cache_filename: str
    cache_data: Any


#
#     def write_to_file(self):
#         with open(self.filename, "wb") as f:
#             pickle.dump(self.filedata, f)
#
#     def recieve_from_file(self) -> Any:
#         with open(self.filename, "wb") as f:
#             return pickle.load(f)
#
#
cache_data: list[data] = []


def cache(prefix_name: str = "", extension: str = "pickle", persistent: bool = False):
    # # if cache_directory not in (x.name for x in _basepath.iterdir()):
    # try:
    #     Path(cache_directory).mkdir()
    # except FileExistsError:
    #     pass

    if not os.path.exists(cache_directory):
        os.makedirs(cache_directory)

    def file_cache_decorator(annotated_function: TCallable) -> TCallable:
        @functools.wraps(annotated_function)
        def wrapper(*args, **kwargs):
            function_signature = calculate_sha(
                inspect.getsource(annotated_function)
                + "".join(str(x) for x in args)
                + "".join(f"{x[0]}{x[1]}" for x in kwargs.items())
            )

            cache_file = (
                # f"{cache_directory}/{prefix_name}cache-{function_signature}.{extension}"
                f"{prefix_name}cache-{function_signature}.{extension}"
            )

            if os.path.exists(cache_file):
                with open(cache_file, "rb") as f:
                    return pickle.load(f)
            elif not persistent:
                global cache_data
                recieved_value = annotated_function(*args, **kwargs)
                cache_data.append(data(cache_file, recieved_value))
                return recieved_value
            else:
                recieved_value = annotated_function(*args, **kwargs)
                with open(cache_file, "wb") as f:
                    pickle.dump(recieved_value, f)
                return recieved_value

        return cast(TCallable, wrapper)

    return file_cache_decorator


def write_cache_to_file():
    for data in cache_data:
        with open(data.cache_filename, "wb") as f:
            pickle.dump(data.cache_data, f)


_ = atexit.register(write_cache_to_file)

# def cache_cleanup():
#     os.removedirs

# def total_time(func):
#     def wrapper():
#         start = time.perf_counter()
#         func()
#         elapsed = time.perf_counter() - start
#
#     return wrapper


if __name__ == "__main__":

    @cache
    def get_result(delay: int) -> str:
        time.sleep(delay)
        return str(delay)

    print(get_result(1))
    print(get_result(2))
