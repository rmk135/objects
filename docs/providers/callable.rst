Callable provider
=================

.. meta::
   :keywords: Python,DI,Dependency injection,IoC,Inversion of Control,Function,Method,Example
   :description: Callable provider helps to make dependencies injection into functions. This page
                 demonstrates how to use a Callable provider.

.. currentmodule:: dependency_injector.providers

:py:class:`Callable` provider calls a function, a method or another callable.

.. literalinclude:: ../../examples/providers/callable.py
   :language: python
   :lines: 3-


If you would like to inject :py:class:`Callable` instance to a service using :py:class:`Provide` and the wiring
mechanism, then you should use the ``.provider`` field. This way :py:class:`Callable` instance will not be called
when being provided, and the service can deliver their own additional arguments.

.. literalinclude:: ../../examples/providers/callable_reusable.py
   :language: python
   :lines: 3-

``Callable`` provider handles an injection of the dependencies the same way like a
:ref:`factory-provider`.

.. disqus::
