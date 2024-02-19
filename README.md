# Tydi-lang-2-Chisel

Tydi-lang-2-Chisel is a transpiler that takes [tydi-lang-2](https://github.com/twoentartian/tydi-lang-2)'s `json` output of a Tydi-lang description and converts it to Chisel code that uses [Tydi-Chisel](https://github.com/abs-tudelft/Tydi-Chisel). See the Tydi-Chisel repo for more details.

In total, the process looks as follows:
1. Create a Tydi-lang system description (`td` file) of the data-types, streams, interfaces (`streamlets`), and components (`impl`ementations).
2. Compile the `td` file with `tydi-lang-complier -c .\tydi_project.toml` with configuration file specifying the `td` sources and top level implementation.
    1. Acquire the executable by cloning and compiling the project (e.g. `cargo build`).
3. Generate Chisel code with e.g.
    ```shell
    python tydi-lang-2-chisel.py ./output ./td-json-output/json_IR.json
    ```
4. Use the resulting Chisel code in your project.

Check `python tydi-lang-2-chisel.py -h` to see options. Multiple input files can be specified. These are all processed individually. If no input file is specified, an `stdin` input is expected.
