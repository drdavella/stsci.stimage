""" This module contains the Node, Edge, and Path
  helper classes used with a Graph class that supports
  segmented graph tables with a recursion functionality
  for generating all possible obsmodes supported by
  the table.
  """
from __future__ import division
from collections import defaultdict
import os
import numpy
import pyfits
#from pysynphot import locations

rules_dict = {
  'default': {'junk': ['', 'None', 'default'], 'exclude': ['aper#']},
  'acs,hrc': {'junk': [], 'exclude': []},
  'acs,hrc,f555w': {'junk': [], 'exclude': []},
  'acs,sbc': {'junk': [], 'exclude': []},
  'acs,wfc1': {'junk': ['wfc1'], 'exclude': ['wfc2']},
  'acs,wfc2': {'junk': ['wfc2'], 'exclude': ['wfc1']},
  'wfc3,uvis1': {'junk': ['uvis1'], 'exclude': ['uvis2']},
  'wfc3,uvis2': {'junk': ['uvis2'], 'exclude': ['uvis1']},
  'wfc3,ir': {'junk': [], 'exclude': []},
  'nicmos,1': {'junk': [], 'exclude': []},
  'nicmos,2': {'junk': [], 'exclude': []},
  'nicmos,3': {'junk': [], 'exclude': []},
  'cos,boa': {'junk': [], 'exclude': []},
  'cos,psa': {'junk': [], 'exclude': []},
  'wfpc2,*': {'junk': [], 'exclude': []},
  'stis,*': {'junk': [], 'exclude': []}
}

class ObsmodeError(BaseException):
  pass

class Node(object):
  """A Node correspondes to a graph table 'innode'.
    Nodes are attached to each other by Edges.
    """
  def __init__(self, name):
    """name = innode""" 
    self.name = name
    self.edges = dict()
    self.edgeset = set()
  
  def __iter__(self):
    return self.edges.values().__iter__()
  
  def __str__(self):
    return str(self.name)
  
  def add_edge(self, edge):
    #The dict is used to select edge based on kwd
    self.edges[edge.kwd] = edge
    #The set is used for fast matching in .select_edge()
    self.edgeset.add(edge.kwd)
  
  def select_edge(self, kwdset, partial=False, count=0):
    # based on algorithm by Alex Martelli
    # kwdset = set of the comma-separated keywords
    # in an obsmode. eg
    # "acs,hrc,f555w" -> set(["acs","hrc","f555w"])
    match = self.edgeset & kwdset
    if len(match) > 1:
      print "Found match of ",match
      raise ValueError("Ambiguous...Too many edges match. Check for problems with graph table.")
    elif len(match) == 1:
      ans = self.edges[match.pop()]
    else:
      # pick up the default if there is one
      if 'default' in self.edges:
        #try:
        if not partial or (partial and count < len(kwdset)):
          #consider 'default' -> None
          ans = self.edges['default']
        else:
          # define Edge object to serve as sentinal to mark the end of this path
          ans = Edge('default',[None,None,None,None],None)
      #except KeyError:
      else:
        # An example of this case would be kwdset=['acs'] yet 
        # the only edges for continuing are ['wfc2','sbc','wfc1','hrc']
        #raise KeyError("No match, bla bla")
        print "No match... Multiple edges but no default."
        # define Edge object to serve as sentinal to mark the end of this path
        ans = Edge('default',[None,None,None,None],None)
    return ans

class Edge(object):
  """An Edge connects a pair of nodes. An Edge
    contains a keyword, compname, and thcompname.
    """
  def __init__(self, kwd, contents, outnode):
    self.kwd = kwd
    self.optical, self.thermal,self.filename,self.pvar=contents
    self.destination = outnode

class Path(object):
  """A Path is produced by traversing a Graph.
    It contains a list of edges and has some convenience
    methods.
    """
  
  def __init__(self, obsmode, params=None):
    self.name = obsmode
    self._edgelist = []
    self._params = params
    self.offset = None
  
  def append(self, edge):
    self._edgelist.append(edge)
    parvalues = []
    parname = edge.filename
    if edge.pvar in self._params and edge.pvar not in [None,'',' ']:
      # Get throughput file for component
      f = pyfits.open(edge.filename)
      cnames = f[1].data.names[1:]
      for pname in cnames:
        if edge.pvar in pname:
          parvalues.append(float(pname.split('#')[-1]))
      f.close()
      self._params[edge.pvar] = parvalues
  
  def __iter__(self):
    return self._edgelist.__iter__()
  
  def compnames(self):
    """Return list of optical compnames"""
    ans = [e.optical for e in self._edgelist if e.optical is not None]
    return ans

class Graph(object):
  """A Graph is the data structure that corresponds to
    the graph table.
    """
  def __init__(self, nodes=None, name=None):
    # fundamental contents
    self.nodes = dict()
    self.name = name
    # metadata usual for use with real graphtabs
    self.tmcfiles = list()
    self.tmtfiles = list()
    self.area = None
    # constructed data usual for use with real graphtabs
    self.lookup = dict()
    
    if nodes is not None:
      for k in nodes:
        self.add_node(k)
      self.top = nodes[0]
    
    self.obsmodes = []
  
  def __len__(self):
    return len(self.nodes)
  
  def add_node(self, node):
    self.nodes[node.name] = node
  
  def __getitem__(self, nodename):
    return self.nodes[nodename]
  
  def __contains__(self, nodename):
    return (nodename in self.nodes)
  
  def get(self, nodename, default=None):
    return self.nodes.get(nodename, default)
  
  def traverse(self, obsmode, verbose=True,partial=False):
    """ This is the usual way to traverse a graph
    table. obsmode_str is a comma-separated obsmode
    string, such as 'acs, hrc, f555w'.
    
    If 'partial' == True, logic will be followed to identify the
    point at which all components of the partial obsmode provided as input
    are found to match at least 1 keyword. 
    
    """
    
    #counter for sanity check
    count=0
    # counter for number of obsmode elements found in graphtab
    kwdcount = 0
    
    #Turn obsmode into a keyword set
    kwdset = set(obsmode.split(','))
    
    #Handle parameterized kwds here
    plist = [k for k in kwdset if '#' in k]
    params = dict()
    for p in plist:
      kwdset.remove(p)
      k,v = p.split('#')
      k += '#'  # needed to match syntax used in graphtab
      params[k.upper()] = v #floated?, always use uppercase for matching
      kwdset.add(k)
    
    #Path to accumulate answers
    ans = Path(obsmode, params=params)
    
    #Start at the top of the tree
    innode = self[self.top.name]
    if verbose:
      print "Starting: ", innode.name
    
    edge_list=[]
    
    while ( (innode is not None) and
           (count <= len(self)) ):
      # Choose edge based on obsmode
      try:
        edge = innode.select_edge(kwdset,partial=partial,count=kwdcount)
      except KeyError:
        # came to the end of the obsmode in the middle of the graph
        break
      ans.append(edge)
      
      if verbose:
        print "->".join([str(innode),
                         str(edge.kwd),
                         str(edge.destination)])
      
      # Count up the number of obsmode elements accounted for in the Path
      if edge.kwd in kwdset and edge.kwd not in set(edge_list) and edge.kwd != 'default': 
        kwdcount += 1
        # Keep track of the offset to this node 
        if edge.destination is not None:
          ans.offset = edge.destination.name
      
      edge_list.append(edge.kwd)
      
      # Set up for passing through this node to the next
      innode = edge.destination
      count+=1
    
    return ans
  
  def get_obsmodes(self,obsmode,prefix=False):
    """UI to the recursive process of obtaining
    all obsmodes in the graph. First calls the
    recurse method, then calls a post-processor
    to remove Nones and duplicates.
    
    If no value is provided for `offset`, then
    it will start at the offset used to 
    read in the graph. If a string is provided
    as the value for `offset`, then .traverse().offset
    will be determined and used. 
    
    The returned obsmode strings will contain the 
    full obsmode if a string is provided for `offset`
    and `prefix`=True.
    
    """
    if self.obsmodes != []:
      self.obsmodes = []
    
    if obsmode in rules_dict.keys():
      self.obsrules_key = obsmode
    elif obsmode + ',*' in rules_dict.keys():
      self.obsrules_key = obsmode + ',*'
    else:
      raise ObsmodeError('Unsupported obsmode string: ' + unicode(obsmode))
    
    self.obsrules_junk = rules_dict['default']['junk'] + \
                          rules_dict[self.obsrules_key]['junk']
    self.obsrules_excl = rules_dict['default']['exclude'] + \
                          rules_dict[self.obsrules_key]['exclude']
                          
    # make sure the given obsmode string doesn't contain anything excluded
    for o in obsmode.split(','):
      if o in self.obsrules_excl:
        s = 'Entered obsmode includes excluded parameters: ' + unicode(obsmode)
        raise ObsmodeError(s)
    
    instrmode=None
    
    if isinstance(obsmode, str):
      if prefix: 
        instrmode=obsmode
      offset = self.traverse(obsmode,verbose=False,partial=True).offset
      
#    print 'Start at offset: ',offset
      
    startnode = self[offset]
    # build up raw list of all possible obsmodes
    self.recurse(startnode)
    
    # remove junk from obsmode strings
    self.process(prefix=instrmode)
    
    return self.obsmodes
#    return real_result
  
  def process(self,prefix=None):
    """
    Remove 'default' strings and put on the prefix, if supplied.
    """
    
    # convert to a numpy array so we can use fast vectorized functions
    self.obsmodes = numpy.array(self.obsmodes, dtype=numpy.str)
    
    # remove junk
    for junk in self.obsrules_junk:
      if junk == '':
        j = ',,'
        r = ','
      else:
        j = junk + ','
        r = ''

      self.obsmodes = numpy.char.replace(self.obsmodes, j, r)
    
    # add prefix (or not) and convert back to list
    if prefix is not None:
      self.obsmodes = numpy.char.add(prefix,self.obsmodes)
      self.obsmodes = [prefix] + self.obsmodes.tolist()
    
    else:
      self.obsmodes = self.obsmodes.tolist()
  
  def read_rules(self, fname):
    """
      """
    # read the data file
    f = open( fname, 'r')
    
    datastr = f.read()
    f.close()
    
    # convert DOS file to Unix - otherwise the eval will fail
    datastr = datastr.replace('\r','')
    
    # try to eval the data
    try :
      datadict = eval(datastr)
    except Exception, e:
      print 'EXCEPTION:',e
      print 'cannot eval data in file ',fname
      raise
    
    return datadict
  
  def recurse(self, node, so_far=None):
    """This is the method that can be used to
    generate all possible obsmodes from a table
    (starting either from the root or from a
    specified node).
    
    This version returns a list of strings that
    must be processed to remove junk.
    """
    
    if so_far is None:
      so_far = ''            
    
    if node is not None:
      #print "Entering node ",node.name
      #Recurse through all the edges of this node
      for edge in node:
        if edge.kwd in self.obsrules_excl:
          continue
          
        #print "Processing node ",node.name, ", edge ",edge.kwd
        further = so_far + "," + edge.kwd
        
        if edge.kwd not in self.obsrules_junk:
          self.obsmodes.append(further)
        
        self.recurse(edge.destination,further)