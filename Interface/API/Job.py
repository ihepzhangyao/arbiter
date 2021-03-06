import os
from arbiter.Core.Workflow.Workflow import *
from arbiter.Core.Utilities.ReturnValues import *
from arbiter.Core.Utilities.Utilities import *
from arbiter.Core.Utilities.dataBaseTools import *
from arbiter.Core.Utilities.Constants import *

class Job:

  def __init__( self, name = None, script = None ):

    global tempDirectory
    self.tempDirectory = tempDirectory
    self.name = None
    self.jobNum = None
    self.workDirectory = os.getcwd()
    self.status = 'unSubmitted'
    self.user = ''
    self.stepCount = 0
    self.workflow = Workflow()
    self.dbTool = dbTool()
    if script:
      self.loadJob( script )
      checkUserName( self.user )
    else:
      if name:
        self.setName( name )
      else:
        self.setName( 'unDefined' )
      self.workflow.jobName = name
    self.createJob()

  def createJob( self ):
    if self.jobNum != None:
      return S_OK( 'Job already created' )
    else:
      newNumString = str( self.dbTool.getNewWorkflowNum() )
      dirDirectory = self.tempDirectory + 'workflowTemp/'
      os.chdir( dirDirectory )
      os.mkdir( newNumString )
      self.user = getUserName()
      self.jobNum = int( newNumString )
      self.workflow.jobNum = self.jobNum
      self.workflow.user = self.user
      self.dbTool.addJob( self )

  def loadJob( self, script ):
    result = loadJobFromXML( self, script )
    return result

  def setName( self, jobName ):

    if not type( jobName ) == type( ' ' ):
      return S_ERROR( 'Expected a string for job name' )
    else:
      self.name = jobName
      return S_OK()

  def addStep( self, sinfo ):

    stepInfoList = sinfo.split('/')
    stepType = stepInfoList[0]
    stepName = stepInfoList[1]

    if stepType not in self.workflow.typeList:
      return S_ERROR( 'There is no %s step type' % stepType )
    self.workflow.addStep( stepType, stepName, self.jobNum )
    self.stepCount += 1
    self.dbTool.addStep( self )
    return S_OK()

  def setStepParameter( self, stepUserName, name, value, extra = None, ptype = None ):
    for step in self.workflow.steps:
      if stepUserName == step.userName:
        if name == 'optionFileDirectory':
          if not value:
            value = self.workDirectory
        step.setParameter( name, value, ptype, extra)
        if name == 'input':
          step.setInputData()
        return S_OK()
    return S_ERROR('Can not find step named %s' % stepUserName )

  def setStepSplitter( self, stepName, splitterInfo ):
    for step in self.workflow.steps:
      if stepName == step.userName:
        step.setSplitter( splitterInfo )
        return S_OK()
    return S_ERROR('Can not find step named %s' % stepName )

  def toXMLFile( self ):
    ret = self.workflow.toXML()
    xmlFile = open( self.tempDirectory + str( self.jobNum ) + '.xml', 'w' )
    xmlFile.write( ret )
    xmlFile.close()
    print self.jobNum
 
  def updateDB( self ):
    for stepNum in range( self.stepCount ):
      stepStatus = checkStepStatus( self.jobNum, stepNum )
      statusDict = { self.jobNum : { stepNum: { 'status' : stepStatus } } }
      self.dbTool.updateStep( statusDict )
    workflowStatus = checkWorkflowStatus( self.jobNum )
    workflowInfo = { 'jobNum' : self.jobNum, 'status' : workflowStatus }
    self.dbTool.updateWorkflow( workflowInfo )    

  def execute( self ):
    optionList = self.workflow.creatCode()
    self.workflow.execute( optionList[0] )

  def reexecute( self, infoDict ):
    for k,v in infoDict.items():
      opstep = self.workflow.steps[int( k )]
      stepName = opstep.name
      optionDirectory = ''
      for p in opstep.parameters:
        if p.name == 'optionFileDirectory':
          if p.value[-1] == '/':
            optionTempDirectory = p.value
          else:
            optionTempDirectory = p.value + '/'
      if not optionDirectory:
        optionDirectory = self.tempDirectory + 'workflowTemp/' + str( self.jobNum ) + '/' + stepName + '/'
      for optionFile in v:
        os.chdir( optionDirectory )
        os.system( 'boss.exe %s' % optionFile )

  def submit( self ):
    optionList = self.workflow.creatCode()
    self.workflow.submit( optionList[0] )
    statusDict = { self.jobNum : { 0 : { 'onGoing' : 'yes' } } }
    self.dbTool.updateStep( statusDict )

  def generate( self ):
    optionList = self.workflow.creatCode()
