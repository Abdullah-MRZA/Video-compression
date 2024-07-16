import time
from typing import TypeVar, Callable, cast
import functools
import os
import pickle
import inspect
from hashlib import sha256


def calculate_sha(text: str) -> str:
    sha_value = sha256(text.encode()).hexdigest()
    return sha_value


TCallable = TypeVar("TCallable", bound=Callable)


def file_cache(annotated_function: TCallable) -> TCallable:
    @functools.wraps(annotated_function)
    def wrapper(*args, **kwargs):
        function_signature = calculate_sha(
            inspect.getsource(annotated_function)
            + "".join(str(x) for x in args)
            + "".join(f"{x[0]}{x[1]}" for x in kwargs.items())
        )
        cache_file = f"cache-{function_signature}.pickle"
        if os.path.exists(cache_file):
            with open(cache_file, "rb") as f:
                return pickle.load(f)
        else:
            recieved_value = annotated_function(*args, **kwargs)
            with open(cache_file, "wb") as f:
                pickle.dump(recieved_value, f)
            return recieved_value

    return cast(TCallable, wrapper)


# def total_time(func):
#     def wrapper():
#         start = time.perf_counter()
#         func()
#         elapsed = time.perf_counter() - start
#
#     return wrapper


if __name__ == "__main__":

    @file_cache
    def get_result(delay: int) -> str:
        time.sleep(delay)
        return str(delay)

    print(get_result(1))
    print(get_result(2))
