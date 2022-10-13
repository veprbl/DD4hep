# ==========================================================================
#  AIDA Detector description implementation
# --------------------------------------------------------------------------
# Copyright (C) Organisation europeenne pour la Recherche nucleaire (CERN)
# All rights reserved.
#
# For the licensing terms see $DD4hepINSTALL/LICENSE.
# For the list of contributors see $DD4hepINSTALL/doc/CREDITS.
#
# ==========================================================================
from __future__ import absolute_import, unicode_literals
from dd4hep_base import *  # noqa: F401, F403


logger = None


def loadDDDigi():
  global logger
  import ROOT
  import dd4hep_base
  from ROOT import gSystem

  logger = dd4hep_base.dd4hep_logger('dddigi')

  # Try to load libglapi to avoid issues with TLS Static
  # Turn off all errors from ROOT about the library missing
  if('libglapi' not in gSystem.GetLibraries()):
    orgLevel = ROOT.gErrorIgnoreLevel
    ROOT.gErrorIgnoreLevel = 6000
    gSystem.Load("libglapi")
    ROOT.gErrorIgnoreLevel = orgLevel

  import os
  import platform
  if platform.system() == "Darwin":
    gSystem.SetDynamicPath(os.environ['DD4HEP_LIBRARY_PATH'])
  #
  # load with ROOT the DDDigi plugin library, which in turn loads the DDigi module
  result = gSystem.Load("libDDDigiPlugins")
  if result < 0:
    raise Exception('DDDigi.py: Failed to load the DDDigi library libDDDigiPlugins: ' + gSystem.GetErrorStr())
  logger.info('DDDigi.py: Successfully loaded DDDigi plugin library libDDDigiPlugins!')
  #
  # import with ROOT the I/O module to read DDG4 output
  result = gSystem.Load("libDDDigi_DDG4_IO")
  if result < 0:
    raise Exception('DDDigi.py: Failed to load the DDG4 IO library libDDDigi_DDG4_IO: ' + gSystem.GetErrorStr())
  logger.info('DDDigi.py: Successfully loaded DDG4 IO plugin library libDDDigi_DDG4_IO!')
  #
  # import the main dd4hep module from ROOT
  from ROOT import dd4hep as module
  return module


# We are nearly there ....
current = __import__(__name__)


def _import_class(ns, nam):
  scope = getattr(current, ns)
  setattr(current, nam, getattr(scope, nam))


# ---------------------------------------------------------------------------
#
try:
  dd4hep = loadDDDigi()
except Exception as X:
  logger.error('+--%-100s--+' % (100 * '-',))
  logger.error('|  %-100s  |' % ('Failed to load DDDigi library:',))
  logger.error('|  %-100s  |' % (str(X),))
  logger.error('+--%-100s--+' % (100 * '-',))
  exit(1)

core = dd4hep
digi = dd4hep.digi
Kernel = digi.KernelHandle
Interface = digi.DigiActionCreation
Detector = core.Detector


# ---------------------------------------------------------------------------
def _constant(self, name):
  return self.constantAsString(name)


Detector.globalVal = _constant
# ---------------------------------------------------------------------------


def importConstants(description, namespace=None, debug=False):
  """
  Import the Detector constants into the dddigi namespace
  """
  ns = current
  if namespace is not None and not hasattr(current, namespace):
    import imp
    m = imp.new_module('dddigi.' + namespace)
    setattr(current, namespace, m)
    ns = m
  evaluator = dd4hep.g4Evaluator()
  cnt = 0
  num = 0
  todo = {}
  strings = {}
  for c in description.constants():
    if c.second.dataType == 'string':
      strings[c.first] = c.second.GetTitle()
    else:
      todo[c.first] = c.second.GetTitle().replace('(int)', '')
  while len(todo) and cnt < 100:
    cnt = cnt + 1
    if cnt == 100:
      logger.info('%s %d out of %d %s "%s": [%s]\n+++ %s' %
                  ('+++ FAILED to import',
                   len(todo), len(todo) + num,
                   'global values into namespace',
                   ns.__name__, 'Try to continue anyway', 100 * '=',))
      for k, v in todo.items():
        if not hasattr(ns, k):
          logger.info('+++ FAILED to import: "' + k + '" = "' + str(v) + '"')
      logger.info('+++ %s' % (100 * '=',))

    for k, v in todo.items():
      if not hasattr(ns, k):
        val = evaluator.evaluate(v)
        status = evaluator.status()
        if status == 0:
          evaluator.setVariable(k, val)
          setattr(ns, k, val)
          if debug:
            logger.info('Imported global value: "' + k + '" = "' + str(val) + '" into namespace' + ns.__name__)
          del todo[k]
          num = num + 1
  if cnt < 100:
    logger.info('+++ Imported %d global values to namespace:%s' % (num, ns.__name__),)


# ---------------------------------------------------------------------------
def _getKernelProperty(self, name):
  ret = Interface.getPropertyKernel(self.get(), name)
  if ret.status > 0:
    return ret.data
  elif hasattr(self.get(), name):
    return getattr(self.get(), name)
  elif hasattr(self, name):
    return getattr(self, name)
  msg = 'DigiKernel::GetProperty [Unhandled]: Cannot access Kernel.' + name
  raise KeyError(msg)


# ---------------------------------------------------------------------------
def _setKernelProperty(self, name, value):
  if Interface.setPropertyKernel(self.get(), str(name), str(value)):
    return
  msg = 'DigiKernel::SetProperty [Unhandled]: Cannot set Kernel.' + name + ' = ' + str(value)
  raise KeyError(msg)


# ---------------------------------------------------------------------------
def _kernel_terminate(self):
  return self.get().terminate()


# ---------------------------------------------------------------------------
Kernel.__getattr__ = _getKernelProperty
Kernel.__setattr__ = _setKernelProperty
Kernel.terminate = _kernel_terminate
# ---------------------------------------------------------------------------
ActionHandle = digi.ActionHandle


# ---------------------------------------------------------------------------
def Action(kernel, nam, parallel=False):
  obj = Interface.createAction(kernel, str(nam))
  obj.parallel = parallel
  return obj


# ---------------------------------------------------------------------------
def EventAction(kernel, nam, parallel=False):
  obj = Interface.createEventAction(kernel, str(nam))
  obj.parallel = parallel
  return obj
# ---------------------------------------------------------------------------


def TestAction(kernel, nam, sleep=0):
  obj = Interface.createEventAction(kernel, str('DigiTestAction/' + nam))
  if sleep != 0:
    obj.sleep = sleep
  return obj
# ---------------------------------------------------------------------------


def ActionSequence(kernel, nam, parallel=False):
  obj = Interface.createSequence(kernel, str(nam))
  obj.parallel = parallel
  return obj
# ---------------------------------------------------------------------------


def Synchronize(kernel, nam, parallel=False):
  obj = Interface.createSync(kernel, str(nam))
  obj.parallel = parallel
  return obj
# ---------------------------------------------------------------------------


def _setup(obj):
  def _adopt(self, action):
    getattr(self,'__adopt')(action.get())
  _import_class('digi', obj)
  cls = getattr(current, obj)
  setattr(cls, '__adopt', getattr(cls, 'adopt'))
  setattr(cls, 'adopt', _adopt)
  # setattr(cls,'add',_adopt)
  return cls


def _get(self, name):
  a = Interface.toAction(self)
  ret = Interface.getProperty(a, name)
  if ret.status > 0:
    return ret.data
  elif hasattr(self.action, name):
    return getattr(self.action, name)
  elif hasattr(a, name):
    return getattr(a, name)
  msg = 'DDDigiAction::GetProperty [Unhandled]: Cannot access property ' + a.name() + '.' + name
  raise KeyError(msg)


def _set(self, name, value):
  """This function is called when properties are passed to the c++ objects."""
  import dd4hep as dd4hep
  a = Interface.toAction(self)
  name = dd4hep.unicode_2_string(name)
  value = dd4hep.unicode_2_string(value)
  if Interface.setProperty(a, name, value):
    return
  msg = 'DDDigiAction::SetProperty [Unhandled]: Cannot set ' + a.name() + '.' + name + ' = ' + value
  raise KeyError(msg)


def _props(obj, **extensions):
  _import_class('digi', obj)
  cls = getattr(current, obj)
  for extension in extensions.items():
    setattr(cls, extension[0], extension[1])
  cls.__getattr__ = _get
  cls.__setattr__ = _set
  return cls


_setup('DigiActionSequence')
_setup('DigiSynchronize')

_import_class('digi', 'DigiKernel')
_import_class('digi', 'DigiContext')
_import_class('digi', 'DigiAction')
_import_class('digi', 'DigiEventAction')
_import_class('digi', 'DigiInputAction')

_props('ActionHandle')
_props('EventActionHandle')
_props('InputActionHandle')
_props('ActionSequenceHandle')
_props('SynchronizeHandle')


def adopt_sequence_action(self, name, **options):
  kernel = Interface.createKernel(Interface.toAction(self))
  action = EventAction(kernel, name)
  for option in options.items():
    setattr(action, option[0], option[1])
  self.adopt(action)
  return action


_props('DigiSynchronize')
_props('DigiActionSequence', adopt_action=adopt_sequence_action)
_props('DigiParallelActionSequence', adopt_action=adopt_sequence_action)
_props('DigiSequentialActionSequence', adopt_action=adopt_sequence_action)


# Need to import digitize late, since it cross includes dddigi
Digitize = None
try:
  import digitize
  Digitize = digitize.Digitize
except Exception as X:
  logger.error('Failed to import digitize: ' + str(X))