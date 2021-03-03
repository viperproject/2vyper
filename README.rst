
2vyper is an automatic verifier for smart contracts written in Vyper, based on the `Viper <http://viper.ethz.ch>`_ verification infrastructure. It is being developed at the `Programming Methodology Group <http://www.pm.inf.ethz.ch/>`_ at ETH Zurich. 2vyper was mainly developed by Robin Sierra, Christian Bräm, and Marco Eilers. 

For examples of the provided specification constructs, check out the `examples <tests/resources/examples>`_ and/or read `Robin Sierra's <https://ethz.ch/content/dam/ethz/special-interest/infk/chair-program-method/pm/documents/Education/Theses/Robin_Sierra_MA_Report.pdf>`_ and `Christian Bräm's <https://ethz.ch/content/dam/ethz/special-interest/infk/chair-program-method/pm/documents/Education/Theses/Christian%20Br%C3%A4m_MS_Report.pdf>`_ Master's theses on the tool. We are working on a short tutorial.

Dependencies (Ubuntu Linux, MacOS)
===================================

Install Java >= 11 (64 bit) and Python >= 3.7 (64 bit).

For usage with the Viper's verification condition generation backend Carbon, you will also need to install the .NET / the Mono runtime.

Dependencies (Windows)
==========================

1.  Install Java >= 11 (64 bit) and Python >= 3.7 (64 bit).

2.  Install either Visual C++ Build Tools 2015 (http://go.microsoft.com/fwlink/?LinkId=691126) or Visual Studio 2015. For the latter, make sure to choose the option "Common Tools for Visual C++ 2015" in the setup (see https://blogs.msdn.microsoft.com/vcblog/2015/07/24/setup-changes-in-visual-studio-2015-affecting-c-developers/ for an explanation).


Getting Started
===============

1.  Clone the 2vyper repository::

        git clone https://github.com/viperproject/2vyper
        cd 2vyper/

2.  Create a virtual environment and activate it::

        virtualenv env
        source env/bin/activate
        
3.  Install 2vyper::

        pip install .


Command Line Usage
==================

To verify a specific file from the 2vyper directory, run::

    2vyper [OPTIONS] path-to-file.vy


The following command line options are available::

    ``--verifier``      
                    Selects the Viper backend to use for verification.
                    Possible options are ``silicon`` (for Symbolic Execution) and ``carbon`` 
                    (for Verification Condition Generation based on Boogie).  
                    Default: ``silicon``.

    ``--viper-jar-path``    
                    Sets the path to the required Viper binaries (``silicon.jar`` or
                    ``carbon.jar``). Only the binary for the selected backend is
                    required. We recommend that you use the provided binary 
                    packages installed by default, but you can or compile your own from 
                    source.
                    Expects either a single path or a colon- (Unix) or semicolon-
                    (Windows) separated list of paths. Alternatively, the environment
                    variables ``SILICONJAR``, ``CARBONJAR`` or ``VIPERJAR`` can be set.
     
    ``--z3``            
                    Sets the path of the Z3 executable. Alternatively, the
                    ``Z3_EXE`` environment variable can be set.
                    
    ``--boogie``        
                    Sets the path of the Boogie executable. Required if the Carbon backend
                    is selected. Alternatively, the ``BOOGIE_EXE`` environment variable can be
                    set.    
     
    ``--counterexample``            
                    Produces a counterexample if the verification fails. Currently only works
                    with the default ``silicon`` backend.
                    
    ``--vyper-root``        
                    Sets the root directory for the Vyper compiler.
     
    ``--skip-vyper``            
                    Skips type checking the given Vyper program using the Vyper compiler.
                    
    ``--print-viper``        
                    Print the generated Viper file to the command line.

To see all possible command line options, invoke ``2vyper`` without arguments.


Alternative Viper Versions
==========================

To use a custom version of the Viper infrastructure, follow the
`instructions here <https://bitbucket.org/viperproject/documentation/wiki/Home>`_. Look for
``sbt assembly`` to find instructions for packaging the required JAR files. Use the
parameters mentioned above to instruct 2vyper to use your custom Viper version.
Note that 2vyper may not always work with the most recent Viper version.


Troubleshooting
=======================

1.  On Windows: During the setup, you get an error like ``Microsoft Visual C++ 14.0 is required.`` or ``Unable to fnd vcvarsall.bat``: 

    Python cannot find the required Visual Studio 2015 C++ installation, make sure you have either installed the Build Tools or checked the "Common Tools" option in your regular VS 2015 installation (see above).

2.  While verifying a file, you get a stack trace ending with something like ``No matching overloads found``:

    The version of Viper you're using does not match your version of 2vyper. Try using the the one that comes with 2vyper instead.


Build Status
============

.. image:: https://pmbuilds.inf.ethz.ch/buildStatus/icon?job=2vyper-linux-xenial&style=plastic
   :alt: Build Status
   :target: https://pmbuilds.inf.ethz.ch/job/2vyper-linux-xenial
